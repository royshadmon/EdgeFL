# Use the official Node.js image as the base
FROM node:20

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of your application code
COPY . .

# Expose the port your app runs on (adjust if needed)
EXPOSE 3000

# Start the application
CMD ["npm", "start"]