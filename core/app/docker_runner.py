from dataclasses import dataclass
import datetime
from typing import List

import docker


class DockerException(Exception):
    pass


class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None

    def start(self):
        self.start_time = datetime.datetime.now()

    def end(self):
        self.end_time = datetime.datetime.now()
        self.duration = self.end_time - self.start_time


@dataclass
class DockerResult:
    logs: str
    start_time: str
    end_time: str
    image: str
    command: str


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.timer = Timer()

    def run(self, image: str, command: List[str]) -> DockerResult:
        self.timer.start()

        cont = self._run_async(image, command)
        response = cont.wait()
        logs = cont.logs(stdout=True, stderr=True).decode("utf-8")
        if response.get("StatusCode", 1) != 0:
            raise DockerException(
                f"Container {image}, command :{command} failed \
                    with status {response['StatusCode']} and logs: {logs}"
            )
        cont.remove()

        self.timer.end()
        result = DockerResult(
            logs,
            self.timer.start_time.isoformat(),
            self.timer.end_time.isoformat(),
            image,
            str(command),
        )
        return result

    def run_container(
        self,
        image: str,
        command: List[str],
        *,
        remove: bool = True,
        network_mode: str | None = None,
        volumes: dict | None = None,
        environment: dict | None = None,
        working_dir: str | None = None,
    ) -> DockerResult:
        """
        Extended container runner supporting volumes, env, and network options.
        Returns a DockerResult with combined stdout/stderr logs.
        """
        self.timer.start()

        container = self.client.containers.run(
            image=image,
            command=command,
            remove=False,  # we will remove after reading logs
            stdout=True,
            stderr=True,
            detach=True,
            network_mode=network_mode,
            volumes=volumes or {},
            environment=environment or {},
            working_dir=working_dir,
        )

        response = container.wait()
        logs = container.logs(stdout=True, stderr=True).decode(
            "utf-8", errors="replace"
        )

        if remove:
            try:
                container.remove()
            except Exception:
                pass

        if response.get("StatusCode", 1) != 0:
            raise DockerException(
                f"Container {image}, command :{command} failed "
                + f"with status {response['StatusCode']} and logs: {logs}"
            )

        self.timer.end()
        return DockerResult(
            logs=logs,
            start_time=self.timer.start_time.isoformat(),
            end_time=self.timer.end_time.isoformat(),
            image=image,
            command=" ".join(command),
        )

    def _run_async(
        self, image: str, command: List[str]
    ) -> docker.models.containers.Container:
        print(f"Running container {image} with command: {command}")
        container = self.client.containers.run(
            image=image,
            command=command,
            remove=False,
            stdout=True,
            stderr=True,
            detach=True,
        )
        return container
