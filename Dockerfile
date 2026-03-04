FROM public.ecr.aws/lambda/python:3.12

# Install dependencies directly to /var/task (Lambda's default Python path)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY lambda_function.py .
COPY src/ ./src/

# Set working directory
WORKDIR /var/task

# Set handler
CMD ["lambda_function.lambda_handler"]
