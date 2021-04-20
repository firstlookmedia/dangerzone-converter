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
        self.add_argument("document", help="document to sanitize")
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
    if args.verbose or args.debug:
        cmd_output = None
    else:
        cmd_output = subprocess.DEVNULL
    sanitize_file(args.document, args.safe_dir, args.image, cmd_output)


def sanitize_file(path, safe_dir, image, cmd_output=None):
    DOCKER_HARDENING = ("--network", "none", "--security-opt=no-new-privileges:true")
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "docker",
            "run",
            "-it",  # to get the output
            f"--cidfile={tmpdir}/cidfile",  # to get the container ID
            "--volume",
            os.path.abspath(path) + ":/tmp/input_file",
        ]
        cmd += DOCKER_HARDENING
        cmd += (image, "document-to-pixels-unpriv")
        output = subprocess.check_output(cmd)
        if cmd_output is None:
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

    with tempfile.TemporaryDirectory() as pixel_dir:
        for page in range(1, pages + 1):
            for type in ("rgb", "width", "height"):
                try:
                    subprocess.check_call(
                        (
                            "docker",
                            "cp",
                            f"{container_id}:/tmp/page-{page}.{type}",
                            pixel_dir.name,
                        )
                    )
                except subprocess.CalledProcessError as e:
                    logging.warning("failed to copy file %s: %s", type, e)
        subprocess.run(
            ("docker", "rm", container_id), check=True, stdout=cmd_output
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "docker",
                "run",
                "-it",  # to get the output
                f"--cidfile={tmpdir}/cidfile",  # to get the container ID
                "--volume",
                f"{pixel_dir.name}:/dangerzone",
                # -e OCR="$OCR" -e OCR_LANGUAGE="$OCR_LANG"
            ]
            cmd += DOCKER_HARDENING
            cmd += (image, "pixels-to-pdf-unpriv")
            subprocess.run(cmd, check=True, stdout=cmd_output)
            with open(f"{tmpdir}/cidfile") as fp:
                container_id = fp.read().strip()

        logging.info("stage 2 completed in container %s", container_id)
        subprocess.check_call(
            (
                "docker",
                "cp",
                f"{container_id}:/tmp/safe-output-compressed.pdf",
                os.path.join(safe_dir, os.path.basename(path)),
            )
        )
        subprocess.run(
            ("docker", "rm", container_id), check=True, stdout=cmd_output
        )


if __name__ == "__main__":
    main()
