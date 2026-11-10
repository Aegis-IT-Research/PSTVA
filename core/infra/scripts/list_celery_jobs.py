import redis
import json
from collections import defaultdict


def list_celery_jobs_redis_service():

    backend_jobs = get_backend_jobs()
    broker_jobs = get_broker_jobs()

    all_jobs = {}
    all_jobs.update(backend_jobs)
    all_jobs.update(broker_jobs)

    return all_jobs


def get_broker_jobs():

    redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
    scheduled = redis_client.lrange("celery", 0, -1)

    grouped_jobs = defaultdict(list)
    for job_string in scheduled:
        job = json.loads(job_string)
        item = {job["headers"]["id"]: job["headers"]}
        grouped_jobs["PENDING"].append(item)
    return grouped_jobs


def get_backend_jobs():

    redis_client = redis.Redis(host="redis", port=6379, db=1, decode_responses=True)
    keys = redis_client.keys("celery-task-meta-*")

    grouped_jobs = defaultdict(list)
    for key in keys:
        job_string = redis_client.get(key)
        job = json.loads(job_string)
        status = job["status"]
        job_id = key.replace("celery-task-meta-", "")
        item = {job_id: job}
        grouped_jobs[status].append(item)
    return grouped_jobs
