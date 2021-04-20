#!/usr/bin/python3

import argparse
import logging
import os
import os.path
import re
import subprocess
import sys
import tempfile


class BatchArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("document", help="document or directory to sanitize")
        self.add_argument(
            "--safe-dir",
            default="safe/",
            help="where to store sanitized files, default: %(default)s",
        )
        self.add_argument(
            "--image",
            default="flmcode/dangerzone",
            help="Docker image to use, default %(default)s",
        )
        self.add_argument(
            "-v",
            "--verbose",
            action=LoggingAction,
            const="INFO",
            help="enable verbose messages",
        )
        self.add_argument(
            "-d",
            "--debug",
            action=LoggingAction,
            const="DEBUG",
            help="enable debugging messages",
        )
        self.add_argument(
            "-n",
            "--dryrun",
            action="store_true",
            help="simulate",
        )


class LoggingAction(argparse.Action):
    """change log level on the fly

    The logging system should be initialized befure this, using
    `basicConfig`.

    Example usage:

    parser.add_argument(
        "-v",
        "--verbose",
        action=LoggingAction,
        const="INFO",
        help="enable verbose messages",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action=LoggingAction,
        const="DEBUG",
        help="enable debugging messages",
    )
    """

    def __init__(self, *args, **kwargs):
        """setup the action parameters

        This enforces a selection of logging levels. It also checks if
        const is provided, in which case we assume it's an argument
        like `--verbose` or `--debug` without an argument.
        """
        kwargs["choices"] = logging._nameToLevel.keys()
        if "const" in kwargs:
            kwargs["nargs"] = 0
        super().__init__(*args, **kwargs)

    def __call__(self, parser, ns, values, option):
        """if const was specified it means argument-less parameters"""
        if self.const:
            logging.getLogger("").setLevel(self.const)
        else:
            logging.getLogger("").setLevel(values)


def main():
    logging.basicConfig(format="%(message)s")
    args = BatchArgParser().parse_args()
    os.makedirs(args.safe_dir, exist_ok=True)
    sanitizer = Sanitizer(safe_dir=args.safe_dir, image=args.image, verbose=args.verbose or args.debug, dryrun=args.dryrun)
    if os.path.isdir(args.document):
        sanitizer.sanitize_dir(dir)
    else:
        sanitizer.sanitize_file(args.document)


class DockerRunner(object):
    "convenience function to call Docker always the same way"
    DOCKER_HARDENING = ("--network", "none", "--security-opt=no-new-privileges:true")

    def __init__(self, image, cmd_output, dryrun):
        self.image = image
        self.cmd_output = cmd_output
        self.dryrun = dryrun

    def run(self, docker_args=[], image=None, args=[]):
        if image is None:
            image = self.image
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "docker",
                "run",
                "-it",
                f"--cidfile={tmpdir}/cidfile",  # to get the container ID
            ]
            cmd += docker_args
            cmd += self.DOCKER_HARDENING
            cmd += [self.image]
            cmd += args
            output = b''
            container_id = None
            if self.dryrun:
                logging.info("dry run, not running: %s", cmd)
            else:
                logging.debug("running command: %s", cmd)
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                for line in p.stdout.readlines():
                    if self.cmd_output or True:
                        print(line.decode("utf-8"), end='')
                    output += line
                if p.wait() != 0:
                    logging.error("failed to run docker command: %s", cmd)
                with open(f"{tmpdir}/cidfile") as fp:
                    container_id = fp.read().strip()
        return container_id, output

    def cp(self, source, target):
        cmd = (
            "docker",
            "cp",
            source,
            target,
        )
        if self.dryrun:
            logging.debug("would run: %s", cmd)
            return
        logging.debug("running: %s", cmd)
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            logging.warning("failed to copy file: %s", e)

    def rm(self, container_id):
        cmd = ("docker", "rm", container_id)
        if self.dryrun:
            logging.debug("would run: %s", cmd)
            return
        logging.debug("running: %s", cmd)
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


class Sanitizer():
    def __init__(self, safe_dir, image, verbose, dryrun):
        self.safe_dir = safe_dir
        self.runner = DockerRunner(image=image, cmd_output=verbose, dryrun=dryrun)

    def sanitize_dir(self, dir):
        for root, dirs, files in os.walk(dir):
            for dir in dirs:
                self.sanitize_dir(dir)
            safe_dir = self.safe_dir + "/" + os.path.basename(root)
            logging.info("processing %d files in dir %s to safe_dir: %s", len(files), root, safe_dir)
            for file in files:
                self.sanitize_file(file)

    def sanitize_file(self, path):
        container_id, output = self.runner.run(
            docker_args=["--volume", os.path.abspath(path) + ":/tmp/input_file"],
            args=["document-to-pixels-unpriv"],
        )

        logging.info("stage 1 completed in container %s", container_id)
        m = re.search(rb"Document has (\d+) pages", output)
        if not m:
            logging.error("failed to find page numbers")
            sys.exit(1)
        pages = int(m.group(1))
        logging.info("generated %d pages", pages)

        with tempfile.TemporaryDirectory() as pixel_dir:
            for page in range(1, pages + 1):
                for type in ("rgb", "width", "height"):
                    self.runner.cp(f"{container_id}:/tmp/page-{page}.{type}", pixel_dir)
            self.runner.rm(container_id)
            container_id, _ = self.runner.run(
                # -e OCR="$OCR" -e OCR_LANGUAGE="$OCR_LANG"
                docker_args=["--volume", f"{pixel_dir}:/dangerzone"],
                args=["pixels-to-pdf-unpriv"],
            )

            logging.info("stage 2 completed in container %s", container_id)
            self.runner.cp(
                f"{container_id}:/tmp/safe-output-compressed.pdf",
                os.path.join(self.safe_dir, os.path.basename(path)),
            )
            self.runner.rm(container_id)


if __name__ == "__main__":
    main()
