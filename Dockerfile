# Use an official Python runtime as a parent image
FROM python:3.6.6

# Set the working directory to /qlik-py-tools
WORKDIR /Data_Analytic_Service_Side_Extension/


# Make port 80 available to the world outside this container
EXPOSE 80 50052


# Run __main__.py when the container launches
CMD ["python", "ExtensionService_helloworld.py"]
