import gzip
import io
import tarfile
from pathlib import Path

import docker

from dotenv import dotenv_values  # pip install python-dotenv


client = docker.from_env()   # uses DOCKER_HOST / socket automatically





class DockerCommands():

    def run(self, image, container_name, port):
        container = client.containers.run(
            image=image,
            name=container_name,
            ports={f"{port}/tcp": int(port)},          # host:container
            restart_policy={"Name": "always"},
            volumes={"/var/run/docker.sock": {  # same as compose bind mount
                "bind": "/var/run/docker.sock",
                "mode": "rw"
            }},
            # environment=env_vars,
            detach=True,                      # don't block; return Container object
            command=[
                    "python", "/app/api-containers/app.py",
                    "--env-file", "/app/deploy_env.env",
                    f"--port", f"{port}"
                ]
        )
        print(container.id)

    def pull_image(self, ref: str):
        """Pull image (e.g. 'edgefl:latest' or 'ghcr.io/org/img:1.0')."""
        print(f"Pulling {ref} …")
        return client.images.pull(ref)

    def save_image(self, image_name: str, out_path: str, compress: bool = False):
        """Save image to a tar (or tar.gz) file."""
        img = client.images.get(image_name)
        data_iter = img.save(named=True)  # stream of bytes

        if compress:
            with gzip.open(out_path, "wb") as f:
                for chunk in data_iter:
                    f.write(chunk)
        else:
            with open(out_path, "wb") as f:
                for chunk in data_iter:
                    f.write(chunk)
        print(f"Saved {image_name} to {out_path}")

    def load_image(self, image_fil: str, image_name: str = "overlay_base", tag: str="temp"):
        """Load image tar (or tar.gz) into local Docker."""
        in_path = Path(image_fil)
        opener = gzip.open if in_path.suffix == ".gz" else open
        with opener(in_path, "rb") as f:
            imgs = client.images.load(f.read())  # returns list of Image objects

        # 2️⃣  pick the first image and tag it
        # img = imgs[0]
        imgs[0].tag(repository=image_name, tag=tag)

        print(f"Loaded {len(imgs)} image(s) from {in_path}")
        return imgs

    def build_overlay(self,
            base_ref: str,
            req_path: str, # requirements.txt path
            data_handler_path: str, # data_handler.py path
            env_path: str, # env file path
            new_tag: str,
            workdir: str = "/app",
    ) -> tuple[str, str]:
        """
        Build a new image on top of *base_ref* with a replacement requirements file.

        Returns (image_id, digest)
        """

        data_handler_file_name = data_handler_path.split("/")[-1]
        env_file_name = env_path.split("/")[-1]
        dockerfile = f"""
        FROM {base_ref}
        WORKDIR {workdir}
        COPY requirements.txt requirements.txt
        COPY {env_file_name} deploy_env.env
        COPY {data_handler_file_name} /app/edgefl/platform_components/data_handlers/{data_handler_file_name} 
        RUN pip install --no-cache-dir -r requirements.txt
        """.lstrip()

        # in-memory build context
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for name, data in {
                "Dockerfile": dockerfile.encode(),
                "requirements.txt": Path(req_path).read_bytes(),
                f"{data_handler_file_name}": Path(data_handler_path).read_bytes(),
                f"{env_file_name}": Path(env_path).read_bytes(),
            }.items():
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                tar.addfile(ti, io.BytesIO(data))
        buf.seek(0)

        img, logs = client.images.build(
            fileobj=buf,
            custom_context=True,
            tag=new_tag,
            rm=True,
            pull=False,
            labels={"rebuilt-by": "overlay_build.py"},
        )
        # Show build output (optional)
        for l in logs:
            if "stream" in l:
                print(l["stream"], end="")

        inspect = client.api.inspect_image(img.id)
        size = inspect.get("Size") / 10**6
        return img.id, f"Size {size} MB"


# Example end-to-end
if __name__ == "__main__":
    dc = DockerCommands()
    image_name = "edgefl:latest"
    # dc.save_image(image_name, out_path="/Users/roy/edgefl_latest.tar")
    #
    # dc.load_image("/Users/roy/edgefl_latest.tar", "my_edgefl_new:latest")
    #

    new_image = "my-new-image:op3"
    dc.build_overlay(base_ref=image_name, req_path="/Users/roy/requirements.txt", data_handler_path="/Users/roy/Github-Repos/EdgeFL/winniio_data_handler.py", env_path="/Users/roy/Github-Repos/EdgeFL/edgefl/env_files/winniio_docker/winniio3.env", new_tag=f'{new_image}')
    container_name = new_image.split(":")[-1]
    if container_name == 'agg':
        port = 8080
    elif container_name == 'op1':
        port = 8081
    elif container_name == 'op2':
        port = 8082
    elif container_name == 'op3':
        port = 8083
    dc.run(new_image, container_name, port=port)
