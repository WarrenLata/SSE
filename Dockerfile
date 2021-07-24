# Use an official Python runtime as a parent image
FROM python:3.6.6

# Set the working directory 
WORKDIR /Data_Analytic_Service_Side_Extension/

# Copy the current directory contents into the container 
COPY . /Data_Analytic_Service_Side_Extension/

# Install required packages
RUN pip install grpcio
RUN pip install grpcio-tools
RUN pip install numpy
RUN pip install scipy
RUN pip install pandas
RUN pip install cython

# Make port 80 available to the world outside this container
EXPOSE 50052


# Run __main__.py when the container launches
CMD ["python", "ExtensionService_helloworld.py"]
