FROM public.ecr.aws/lambda/python:3.11
COPY requirements-aws.txt ${LAMBDA_TASK_ROOT}/requirements-aws.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements-aws.txt
COPY cloudserve/ ${LAMBDA_TASK_ROOT}/cloudserve/
COPY data/development_tickets.json ${LAMBDA_TASK_ROOT}/data/development_tickets.json
COPY data/documentation.json ${LAMBDA_TASK_ROOT}/data/documentation.json
COPY prompts/ ${LAMBDA_TASK_ROOT}/prompts/
CMD ["cloudserve.aws_handler.handler"]
