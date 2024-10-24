import os
import time
from ibmfl.aggregator.aggregator import Aggregator
from ibmfl.party.party import Party

class FLSession:
    def __init__(self, num_parties, dataset, points_per_party, model, t_rounds, fusion_model):
        self.num_parties = num_parties
        self.dataset = dataset
        self.points_per_party = points_per_party
        self.model = model
        self.t_rounds = t_rounds
        self.aggregator = None
        self.parties = []
        self.fusion_model = fusion_model


    def init_party(self, pid):
        party = Party(config_file=f"examples/configs/{self.fusion_model}/{self.model}/config_party{pid}.yml")
        party.start()
        party.register_party()
        party.proto_handler.is_private = False
        return party

    def init_parties(self):
        for i in range(self.num_parties):
            p = self.init_party(i)
            self.parties.append(p)
            time.sleep(0.1)

    def stop_parties(self):
        for p in self.parties:
            p.stop()

    def init_aggregator(self):
        # Generate the data and config files
        os.system(f'python examples/generate_data.py -n {self.num_parties} -d {self.dataset} -pp {self.points_per_party}')
        os.system(f"python examples/generate_configs.py -f {self.fusion_model} -m {self.model} -n {self.num_parties} -d {self.dataset} -p examples/data/{self.dataset}/random")

        # Start aggregator
        self.aggregator = Aggregator(config_file=f"examples/configs/{self.fusion_model}/{self.model}/config_agg.yml")
        self.aggregator.start()

        # Wait for parties to connect

    def run_training(self):
        for round_num in range(1, self.t_rounds + 1):
            print(f">> Training round {round_num}/{self.t_rounds}")
            start = time.time()
            self.aggregator.start_training()
            print(f">> Round {round_num} completed in {time.time() - start} seconds")

        print(">> All rounds completed.")

    def evaluate(self):
        self.aggregator.eval_model()

    def stop_aggregator(self):
        self.aggregator.stop()


if __name__ == "__main__":
    fusion_model = 'iter_avg'
    num_parties = 2
    dataset = "mnist"
    points_per_party = 200
    model = "pytorch"
    t_rounds = 2  # Number of training rounds

    sim = FLSession(num_parties, dataset, points_per_party, model, t_rounds, fusion_model)
    sim.init_aggregator()
    sim.init_parties()
    sim.run_training()
    sim.evaluate()
    sim.stop_aggregator()
    sim.stop_parties()
