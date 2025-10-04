FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt /var/task/requirements.txt
RUN pip install --no-cache-dir -r /var/task/requirements.txt

# Copy function code
COPY handler.py /var/task/handler.py

# ----- Local testing: bake in RIE and set entrypoint -----
# (This ENTRYPOINT also works on AWS because the real service ignores RIE)
COPY lambda-rie /usr/local/bin/aws-lambda-rie
ENTRYPOINT [ "/usr/local/bin/aws-lambda-rie", "/lambda-entrypoint.sh" ]

# Lambda handler (module.function)
CMD [ "handler.lambda_handler" ]
