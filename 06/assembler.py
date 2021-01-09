import argparse

symTable = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "SCREEN": 16384,
    "KBD": 24576,
}
CTable = {
    "0": "101010",
    "1": "111111",
    "-1": "111010",
    "D": "001100",
    "A": "110000",
    "!D": "001101",
    "!A": "110001",
    "-D": "001111",
    "-A": "110011",
    "D+1": "011111",
    "A+1": "110111",
    "D-1": "001110",
    "A-1": "110010",
    "D+A": "000010",
    "A+D": "000010",
    "D-A": "010011",
    "A-D": "000111",
    "D&A": "000000",
    "A&D": "000000",
    "D|A": "010101",
    "A|D": "010101",
}
JTable = {
    "": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}
cnt = 0x000F


def isnumber(st):
    try:
        _ = int(st)
        return True
    except (SyntaxError, ValueError):
        return False


def padding(x, l=16):
    s = bin(int(x))[2:]
    return "".join(["0" for i in range(l - len(s))]) + s


def read_name(st):
    i = st.rfind(".")
    if i == -1:
        raise OSError("file does not have an extension")
    return st[:i]


def readsym(name):
    global cnt
    if name in symTable.keys():
        return symTable[name]
    if len(name) > 1 and name[0] == "R" and isnumber(name[1:]):
        return int(name[1:])
    cnt += 1
    symTable.setdefault(name, cnt)
    return cnt


def translate_A_command(st):
    assert st[0] == "@"
    st = st[1:]
    if isnumber(st):
        return padding(st)
    else:
        return padding(readsym(st))


def translate_C_command(st):
    global JTable, CTable
    i = st.find("=")
    j = st.find(";")
    if i == -1 and j == -1:
        dest = ""
        comp = st
        jmp = ""
    elif i == -1:
        dest = ""
        comp = st[:j]
        jmp = st[j + 1 :]
    elif j == -1:
        dest = st[:i]
        comp = st[i + 1 :]
        jmp = ""
    else:
        dest = st[:i]
        comp = st[i + 1 : j]
        jmp = st[j + 1 :]

    D = ["0", "0", "0"]
    if "A" in dest:
        D[0] = "1"
    if "D" in dest:
        D[1] = "1"
    if "M" in dest:
        D[2] = "1"

    if "M" in comp:
        A = "1"
        comp = comp.replace("M", "A")
    else:
        A = "0"
    C = CTable[comp]
    J = JTable[jmp]

    return "111" + A + C + "".join(D) + J


def new_line_marker(st, pc):
    global symTable
    if st[0] != "(" or st[-1] != ")":
        raise SyntaxError("Missing brackets")

    st = st[1:-1]
    if st in symTable.keys():
        print(st, pc)
        raise SyntaxError("line marker have an ambiguous name")

    symTable.setdefault(st, pc)


def modifyLine(line):
    line = line[:-1]
    i = line.find("//")
    if i != -1:
        line = line[:i]
    line = line.replace(" ", "").replace("\t", "")
    return line


def main():
    parser = argparse.ArgumentParser(description="A hack language assembler")
    parser.add_argument("fin", help="the input assembly language file (ends with .asm)")
    parser.add_argument(
        "-o", default="#", help="(optional) the output machine language file"
    )
    args = parser.parse_args()
    if args.o == "#":
        args.o = read_name(args.fin) + ".hack"
    with open(args.fin, "r") as f:
        code = f.readlines()

    code = [modifyLine(x) for x in code]
    code = list(filter(lambda x: x != "", code))

    pc = 0
    for line, i in zip(code, range(len(code))):
        if line[0] == "(":
            new_line_marker(line, pc)
        else:
            pc += 1

    hack = []
    for line in code:
        if line == "":
            continue
        if line[0] == "@":
            hack.append(translate_A_command(line))
        elif line[0] != "(":
            hack.append(translate_C_command(line))

    with open(args.o, "w") as f:
        for each in hack:
            print(each, file=f)


main()
