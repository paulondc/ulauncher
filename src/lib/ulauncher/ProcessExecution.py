import re
import sys
import select
import subprocess
import codecs

class ProcessExecution(object):
    """
    Executes a process.
    """

    # regex: any alpha numeric, underscore and dash characters are allowed.
    __validateShellArgRegex = re.compile("^[\w_-]*$")

    # using uft-8 as default stream encoding
    __sysStdout = codecs.getwriter("utf-8")(sys.stdout)
    __sysStderr = codecs.getwriter("utf-8")(sys.stderr)

    def __init__(self, args, env={}, shell=True, cwd=None):
        """
        Create an ProcessExecution object.
        """
        self.__stdout = []
        self.__stderr = []
        self.__shell = shell
        self.__cwd = cwd

        self.__setArgs(args)
        self.__setEnv(env)
        self.__createProcess()

    def isShell(self):
        """
        Return the process should run through a shell session.
        """
        return self.__shell

    def env(self):
        """
        Return the environment for the process.
        """
        return self.__env

    def cwd(self):
        """
        Return the current working directory used to launch the process.
        """
        return self.__cwd

    def args(self):
        """
        Return a list of arguments used by the process.
        """
        return self.__args

    def stderr(self):
        """
        Return a list of stderr messages.
        """
        return self.__stderr

    def stdout(self):
        """
        Return a list of stdout messages.
        """
        return self.__stdout

    def executionSuccess(self):
        """
        Return a boolean if the execution has been sucessfull.
        """
        return self.exitStatus() == 0

    def exitStatus(self):
        """
        Return the exist status about the process.
        """
        return self.__process.returncode

    def pid(self):
        """
        Return the process id.
        """
        return self.__process.pid

    def execute(self):
        """
        Execute the process.
        """
        # we want all stream messages to keep going
        # up to system's stream in realtime, instead of
        # showing them only when execution is done
        # (subprocess/communicate default behaviour)
        # https://stackoverflow.com/questions/12270645
        while True:
            reads = [
                self.__process.stdout.fileno(),
                self.__process.stderr.fileno()
            ]

            try:
                ret = select.select(reads, [], [])
                for fd in ret[0]:
                    if fd == self.__process.stdout.fileno():
                        read = self.__process.stdout.readline().decode("utf-8")
                        self.__sysStdout.write(read)
                        self.__stdout.append(read)

                    if fd == self.__process.stderr.fileno():
                        read = self.__process.stderr.readline().decode("utf-8")
                        self.__sysStderr.write(read)
                        self.__stderr.append(read)

            except KeyboardInterrupt:
                reason = ' KeyboardInterrupt\n'
                sys.stderr.write(reason)
                self.__stderr.append(reason)
                break

            if self.__process.poll() is not None:
                break

    def __setArgs(self, args):
        """
        Set a list of arguments that should be used by the process.
        """
        assert isinstance(args, list), "Invalid args list!"

        self.__args = list(args)

    def __setEnv(self, env):
        """
        Set the environment for the process.
        """
        self.__env = dict(env)

    def __createProcess(self):
        """
        Create a process that later should be executed through {@link run}.
        """
        executableArgs = ' '.join(map(str, self.__sanitizeShellArgs(self.args()))) if self.isShell() else self.args()
        self.__process = subprocess.Popen(
            executableArgs,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=self.isShell(),
            env=self.env(),
            cwd=self.cwd()
        )

    @staticmethod
    def __sanitizeShellArgs(args):
        """
        Sanitize shell args by escaping shell special characters.
        """
        result = []

        for index, arg in enumerate(args):

            # we need to avoid to escape the first argument otherwise, it will be
            # interpreted as string rather than a command.
            if index == 0 or ProcessExecution.__validateShellArgRegex.match(arg):
                result.append(arg)
            else:
                result.append('"{}"'.format(arg.replace('"', '\\"')))

        return result
