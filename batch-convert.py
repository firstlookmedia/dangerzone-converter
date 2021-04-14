#!/usr/bin/python3

import argparse
import logging
import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile


class BatchArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("document", help="document to sanitize")
        self.add_argument(
            "--safe-dir",
            default="safe/",
            help="where to store sanitized files, default: %(default)s",
        )
        self.add_argument(
            "--pixel-dir",
            default="pixel/",
            help="where to store temporary files, default: %(default)s",
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
    os.makedirs(args.pixel_dir, exist_ok=True)
    pixel_dir = os.path.abspath(args.pixel_dir)

    DOCKER_HARDENING = ("--network", "none", "--security-opt=no-new-privileges:true")
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "docker",
            "run",
            "-it",  # to get the output
            f"--cidfile={tmpdir}/cidfile",  # to get the container ID
            "--volume",
            os.path.abspath(args.document) + ":/tmp/input_file",
        ]
        cmd += DOCKER_HARDENING
        cmd += (args.image, "document-to-pixels-unpriv")
        output = subprocess.check_output(cmd)
        print(output.decode("utf-8"))
        with open(f"{tmpdir}/cidfile") as fp:
            container_id = fp.read().strip()

    logging.info("stage 1 completed in container %s", container_id)
    m = re.search(rb"Document has (\d+) pages", output)
    if not m:
        logging.error("failed to find page numbers")
        sys.exit(1)
    pages = int(m.group(1))
    logging.info("generated %d pages", pages)

    for page in range(1, pages + 1):
        for type in ("rgb", "width", "height"):
            try:
                subprocess.check_call(
                    (
                        "docker",
                        "cp",
                        f"{container_id}:/tmp/page-{page}.{type}",
                        args.pixel_dir,
                    )
                )
            except subprocess.CalledProcessError as e:
                logging.warning("failed to copy file %s: %s", type, e)
    subprocess.check_call(("docker", "rm", container_id))

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "docker",
            "run",
            "-it",  # to get the output
            f"--cidfile={tmpdir}/cidfile",  # to get the container ID
            "--volume",
            f"{pixel_dir}:/dangerzone",
            # -e OCR="$OCR" -e OCR_LANGUAGE="$OCR_LANG"
        ]
        cmd += DOCKER_HARDENING
        cmd += (args.image, "pixels-to-pdf-unpriv")
        subprocess.check_call(cmd)
        with open(f"{tmpdir}/cidfile") as fp:
            container_id = fp.read().strip()

    logging.info("stage 2 completed in container %s", container_id)
    for path in ("safe-output.pdf", "safe-output-compressed.pdf"):
        subprocess.check_call(
            ("docker", "cp", f"{container_id}:/tmp/{path}", args.safe_dir)
        )
    subprocess.check_call(("docker", "rm", container_id))
    shutil.rmtree(args.pixel_dir)


if __name__ == "__main__":
    main()
