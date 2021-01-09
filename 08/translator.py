import argparse
import os


class Parser:
    commandTypeTable = {
        "label": "C_LABEL",
        "function": "C_FUNCTION",
        "push": "C_PUSH",
        "pop": "C_POP",
        "goto": "C_GOTO",
        "if-goto": "C_IF",
        "return": "C_RETURN",
        "call": "C_CALL",
        "add": "C_ARITHMETIC",
        "sub": "C_ARITHMETIC",
        "neg": "C_ARITHMETIC",
        "eq": "C_ARITHMETIC",
        "gt": "C_ARITHMETIC",
        "lt": "C_ARITHMETIC",
        "and": "C_ARITHMETIC",
        "or": "C_ARITHMETIC",
        "not": "C_ARITHMETIC",
    }

    def __init__(self, fd):
        self.file = fd.readlines()
        self.file = [Parser.modifyLine(x) for x in self.file]
        self.file = list(filter(lambda x: x != "", self.file))
        self.file_length = len(self.file)

        self.index = -1
        self.command = ""
        self.command_type = self.arg_1 = self.arg_2 = ""

    def hasMoreCommands(self):
        return self.index < self.file_length - 1

    def advance(self):
        self.index += 1
        line = self.file[self.index].split(" ")
        self.command = line[0]
        self.command_type = Parser.commandTypeTable[line[0]]
        try:
            self.arg_1 = line[1]
            self.arg_2 = line[2]
        except:
            pass

    def commandType(self):
        return self.command_type

    def arg1(self):
        assert self.command_type != "C_RETURN"
        if self.command_type == "C_ARITHMETIC":
            return self.command
        return self.arg_1

    def arg2(self):
        assert self.command_type in ("C_PUSH", "C_POP", "C_FUNCTION", "C_CALL")
        return int(self.arg_2)

    def modifyLine(line):
        line = line[:-1]
        i = line.find("//")
        if i != -1:
            line = line[:i]

        line = line.replace("\t", "").strip()
        return line


str1 = """@SP
AM=M-1
D=M
A=A-1
M=M$D
"""
str2 = """@SP
AM=M-1
M=$M
@SP
M=M+1
"""
str3 = """@SP
AM=M-1
D=M
A=A-1
D=M-D
@TRUE#
D;$
D=0
@END#
0;JMP
(TRUE#)
D=-1
(END#)
@SP
A=M-1
M=D
"""


class CodeWriter:

    opr_table = {
        "add": "+",
        "sub": "-",
        "and": "&",
        "or": "|",
        "not": "!",
        "neg": "-",
        "eq": "JEQ",
        "gt": "JGT",
        "lt": "JLT",
    }

    seg_table = {"local": "LCL", "argument": "ARG", "this": "THIS", "that": "THAT"}

    def __init__(self, file, isdir):
        self.file = open(file, "w")
        self.index = 0
        self.functionName = ""
        self.return_dict = dict()
        self.multiple = isdir
        self.hasMain = False
        self.mainFunc = ""
        if isdir:
            self.writeInit()

    def setFileName(self, filename):
        self.filename = filename

    def close(self):
        self.file.close()

    def writeInit(self):
        st = ""
        st += "@256\nD=A\n@SP\nM=D\n"
        print(st, file=self.file)
        self.writeCall("Sys.init", 0)

    def writeMain(self):
        if not self.hasMain:
            st = "(Sys.init)\n"
            print(st, file=self.file)
            self.writeCall(self.mainFunc, 0)

    def writeLabel(self, label):
        label = "(" + self.functionName + "$" + label + ")\n"
        print(label, file=self.file)

    def writeGoto(self, label):
        print("@" + self.functionName + "$" + label + "\n0;JMP\n", file=self.file)

    def writeIf(self, label):
        st = "@SP\nAM=M-1\nD=M\n@" + self.functionName + "$" + label + "\nD;JNE\n"
        print(st, file=self.file)

    def _pushSign(self, x):
        return "@" + str(x) + "\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n"

    def writeCall(self, func, argc):
        ret = self.functionName + "$return-address"
        self.return_dict.setdefault(ret, 0)
        self.return_dict[ret] += 1
        ret = ret + str(self.return_dict[ret])
        st = (
            "@"
            + str(ret)
            + "\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n"
            + self._pushSign("LCL")
            + self._pushSign("ARG")
            + self._pushSign("THIS")
            + self._pushSign("THAT")
        )
        st += (
            "@SP\nD=M\n@" + str(argc) + "\nD=D-A\n@5\nD=D-A\n@ARG\nM=D\n"
        )  # ARG=SP-n-5
        st += "@SP\nD=M\n@LCL\nM=D\n"  # LCL=SP
        st += "@" + func + "\n0;JMP\n"  # goto func
        st += "(" + ret + ")\n"
        print(st, file=self.file)

    def writeReturn(self):
        callFrame = "@R13\nD=M\n@{}\nA=D-A\nD=M\n@{}\nM=D\n"
        st = "@LCL\nD=M\n@R13\nM=D\n"
        st += callFrame.format(5, "R14")
        st += "@SP\nAM=M-1\nD=M\n@ARG\nA=M\nM=D\n"  # *ARG=pop()
        st += "@ARG\nD=M+1\n@SP\nM=D\n"        # SP=ARG+1
        st += callFrame.format(1, "THAT")
        st += callFrame.format(2, "THIS")
        st += callFrame.format(3, "ARG")
        st += callFrame.format(4, "LCL")
        st += "@R14\nA=M\n0;JMP\n"
        print(st, file=self.file)

    def writeFunc(self, func, nLocals):
        self.functionName = func
        if func == "Sys.init":
            self.hasMain = True
        else:
            self.mainFunc = func
        st = "(" + func + ")\n"
        st += self._PushPop("push", "constant", 0) * nLocals
        print(st, file=self.file)

    def writeArithmetic(self, cmd):
        st = ""
        if cmd in ("add", "sub", "and", "or"):
            st = str1.replace("$", CodeWriter.opr_table[cmd])
        if cmd in ("not", "neg"):
            st = str2.replace("$", CodeWriter.opr_table[cmd])
        if cmd in ("eq", "gt", "lt"):
            st = str3.replace("$", CodeWriter.opr_table[cmd])
            st = st.replace("#", str(self.index))
            self.index += 1
        print(st, file=self.file)

    def _load_address(self, seg, ind):
        # load the address of some place in register A
        # seg != "constant"
        if seg in ("local", "argument", "this", "that"):
            return "@" + str(ind) + "\nD=A\n@" + CodeWriter.seg_table[seg] + "\nA=D+M\n"
        if seg == "pointer":
            return "@" + str(ind + 3) + "\n"
        if seg == "temp":
            return "@" + str(ind + 5) + "\n"
        if seg == "static":
            return "@" + self.filename + "." + str(ind) + "\n"

    def _PushPop(self, cmd, seg, ind):
        st = ""
        if seg == "constant":
            assert cmd == "push"
            st = "@" + str(ind) + "\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n"
        else:
            st = self._load_address(seg, ind)
            if cmd == "push":
                st += "D=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n"
            else:
                st += "D=A\n@R13\nM=D\n@SP\nAM=M-1\nD=M\n@R13\nA=M\nM=D\n"
        return st

    def writePushPop(self, cmd, seg, ind):
        st = self._PushPop(cmd, seg, ind)
        print(st, file=self.file)


def read_name(st):
    i = st.rfind(".")
    if i == -1:
        raise OSError("file does not have an extension")
    return st[:i]


def read_extension(st):
    i = st.rfind(".")
    if i == -1:
        raise OSError("file does not have an extension")
    return st[i + 1 :]


def main():
    argParser = argparse.ArgumentParser(description="A hack VM parser")
    argParser.add_argument("fin", help="input file (end with .vm) or folder")

    args = argParser.parse_args()
    fin = args.fin
    if os.path.isfile(fin):
        inputFiles = [fin]
        writer = CodeWriter(read_name(fin) + ".asm", False)
    else:
        inputFiles = list(filter(lambda x: read_extension(x) == "vm", os.listdir(fin)))
        writer = CodeWriter(
            os.path.join(fin, os.path.split(fin)[0].split("/")[-1]) + ".asm",
            len(inputFiles) > 1,
        )

    for filename in inputFiles:
        print(filename)
        with open(os.path.join(fin, filename), "r") as fd:
            parser = Parser(fd)
        writer.setFileName(read_name(os.path.basename(filename)))

        while parser.hasMoreCommands():
            parser.advance()
            if parser.commandType() == "C_ARITHMETIC":
                writer.writeArithmetic(parser.arg1())
            if parser.commandType() == "C_POP":
                writer.writePushPop("pop", parser.arg1(), parser.arg2())
            if parser.commandType() == "C_PUSH":
                writer.writePushPop("push", parser.arg1(), parser.arg2())
            if parser.commandType() == "C_FUNCTION":
                writer.writeFunc(parser.arg1(), parser.arg2())
            if parser.commandType() == "C_CALL":
                writer.writeCall(parser.arg1(), parser.arg2())
            if parser.commandType() == "C_RETURN":
                writer.writeReturn()
            if parser.commandType() == "C_GOTO":
                writer.writeGoto(parser.arg1())
            if parser.commandType() == "C_IF":
                writer.writeIf(parser.arg1())
            if parser.commandType() == "C_LABEL":
                writer.writeLabel(parser.arg1())

    if writer.multiple: writer.writeMain()


if __name__ == "__main__":
    main()
