import os
import random


class Token:
    def __init__(self, typ, value, pos):
        self.typ = typ
        self.value = value
        self.pos = pos

    def __str__(self):
        return "Token: type - {}; value - {}; position - {}".format(
            self.typ, self.value, self.pos
        )


class FileReader:
    def __init__(self, filename):
        self.file = open(filename, "r")
        self.buffer = ""
        self.bufferlen = ""
        self.ptr = 0
        self.tempList = []
        self.tempCount = 0
        self.lcount = 0
        self.eof = False

    def fillBuffer(self):
        if self.eof:
            return 0
        if self.ptr == len(self.buffer):
            self.buffer = self.file.readline()
            self.bufferlen = len(self.buffer)
            self.lcount += 1
            if self.bufferlen == 0:
                self.eof = True
                return 0
            self.ptr = 0
        return 1

    def next(self):
        if self.tempCount != 0:
            res = self.tempList[-1]
            self.tempList.pop()
            self.tempCount -= 1
            return res
        if self.eof or not self.fillBuffer():
            self.file.close()
            return 0
        self.ptr += 1
        return self.buffer[self.ptr - 1]

    def feedback(self, c):
        self.tempCount += 1
        self.tempList.append(c)

    def EOF(self):
        return self.eof and self.tempCount == 0

    def position(self):
        return (self.lcount, self.ptr - 1)


class JackTokenizer:
    reserved = {
        "class",
        "method",
        "int",
        "function",
        "boolean",
        "constructor",
        "char",
        "void",
        "var",
        "static",
        "field",
        "let",
        "do",
        "if",
        "else",
        "while",
        "return",
        "true",
        "false",
        "null",
        "this",
    }

    def __init__(self, filename):
        self.fileReader = FileReader(filename)
        self.temp = []

    def skipRemarkLine(self):
        while self.fileReader.next() != "\n":
            pass

    def readIntConst(self):
        st = ""
        while True:
            c = self.fileReader.next()
            if not c.isdigit():
                self.fileReader.feedback(c)
                return int(st)
            st += c

    def readStringConst(self):
        st = ""
        self.fileReader.next()
        while True:
            c = self.fileReader.next()
            if c == '"':
                return st
            st += c

    def readIdentifier(self):
        st = ""
        while True:
            c = self.fileReader.next()
            if not (c.isdigit() or c.isalpha() or c == "_"):
                self.fileReader.feedback(c)
                return st
            st += c

    def skipToNext(self):
        while True:
            c = ""
            while True:
                c = self.fileReader.next()
                if c not in [" ", "\n", "\t"]:
                    break
            if c == 0:
                return
            if c == "/":
                c = self.fileReader.next()
                if c == "/":
                    while self.fileReader.next() != "\n":
                        pass
                elif c == "*":
                    c = self.fileReader.next()
                    d = self.fileReader.next()
                    while not (c == "*" and d == "/"):
                        c = d
                        d = self.fileReader.next()
                else:
                    self.fileReader.feedback(c)
                    self.fileReader.feedback("/")
                    return
            else:
                self.fileReader.feedback(c)
                return

    def hasMoreTokens(self):
        self.skipToNext()
        return not self.fileReader.EOF() or len(self.temp) > 0

    def advance(self):
        if len(self.temp) == 0:
            self.viewNext()
        tmp = self.temp[-1]
        self.temp.pop()
        return tmp

    def viewNext(self):
        if len(self.temp) != 0:
            return self.temp[-1]
        self.skipToNext()
        c = self.fileReader.next()
        self.fileReader.feedback(c)
        if c == '"':
            tmp = Token(
                "STRING_CONST", self.readStringConst(), self.fileReader.position()
            )
        elif c.isdigit():
            tmp = Token("INT_CONST", self.readIntConst(), self.fileReader.position())
        elif c.isalpha() or c == "_":
            st = self.readIdentifier()
            if st in JackTokenizer.reserved:
                tmp = Token("KEYWORD", st, self.fileReader.position())
            else:
                tmp = Token("IDENTIFIER", st, self.fileReader.position())
        else:
            self.fileReader.next()
            tmp = Token("SYMBOL", c, self.fileReader.position())
        self.temp.append(tmp)
        return self.temp[-1]

    def feedback(self, x):
        self.temp.append(x)

    def close(self):
        close(self.file)


class CompilationEngine:
    def __init__(self, infile, outfile):
        self.tokenizer = JackTokenizer(infile)
        self.outfile = open(outfile, "w")
        self.baseIndent = 0
        self.classVarList = set()
        self.subroutineVarList = set()

    def syntaxError(self, pos):
        raise SyntaxError("invalid syntax at {}".format(pos))

    def view(self):
        if not self.tokenizer.hasMoreTokens():
            raise SyntaxError("Missing text at the end of the code!")
        return self.tokenizer.viewNext()

    def fetch(self):
        if not self.tokenizer.hasMoreTokens():
            raise SyntaxError("Missing text at the end of the code!")
        return self.tokenizer.advance()

    def fetchToken(self, typ, value=None):
        tok = self.fetch()
        if type(value) == tuple:
            if tok.typ != typ or tok.value not in value:
                self.syntaxError(tok.pos)
        elif isinstance(value, str):
            if tok.typ != typ or tok.value != value:
                self.syntaxError(tok.pos)
        elif value is None:
            if tok.typ != typ:
                self.syntaxError(tok.pos)
        else:
            if not value(tok):
                self.syntaxError(tok.pos)
        
        self.writeToken(tok)

    def fetchSymbol(self, c):
        self.fetchToken("SYMBOL", c)

    def writeToken(self, x):
        print("\t" * self.baseIndent + "<{0}> {1} </{0}>".format(x.typ.lower(), x.value), file=self.outfile)

    def begin(self, st):
        print("\t" * self.baseIndent + "<" + st + ">", file=self.outfile)
        self.baseIndent += 1

    def end(self, st):
        self.baseIndent -= 1
        print("\t" * self.baseIndent + "</" + st + ">", file=self.outfile)

    def compileClass(self):
        self.begin("class")
        self.fetchToken("KEYWORD", "class")
        self.compileClassName()
        self.fetchSymbol("{")
        while self.view().value in ("static", "field"):
            self.compileClassVarDec()
        while self.view().value in ("constructor", "function", "method"):
            self.compileSubroutineDec()
        self.fetchSymbol("}")
        self.end("class")

    def compileClassVarDec(self):
        self.begin("classVarDec")
        self.fetchToken("KEYWORD", ("static", "field"))
        self.compileType()
        self.compileVarName(self.classVarList)
        while self.view().value == ",":
            self.fetchSymbol(",")
            self.compileVarName(self.classVarList)
        self.fetchSymbol(";")
        self.end("classVarDec")

    def viewIsType(self):
        return self.view().typ == "IDENTIFIER" or self.view().value in (
            "boolean",
            "char",
            "int",
        )

    def viewIsOp(self):
        return self.view().value in "+-*/&|<>="

    def viewIsUnaryOp(self):
        return self.view().value in "-~"

    def compileType(self):
        self.begin("type")
        if self.view().typ == "IDENTIFIER":
            self.fetchToken("IDENTIFIER")
        else:
            self.fetchToken("KEYWORD", ("boolean", "char", "int"))
        self.end("type")

    def compileSubroutineDec(self):
        self.subroutineVarList.clear()
        self.begin("subroutineDec")
        self.fetchToken("KEYWORD", ("constructor", "function", "method"))
        if self.view().value == "void":
            self.fetchToken("KEYWORD", "void")
        else:
            self.compileType()
        self.compileSubroutineName()
        self.fetchSymbol("(")
        self.compileParameterList()
        self.fetchSymbol(")")
        self.compileSubroutineBody()
        self.end("subroutineDec")

    def compileParameterList(self):
        self.begin("parameterList")
        if self.viewIsType():
            self.compileType()
            self.compileVarName(self.subroutineVarList)
            while self.view().value == ",":
                self.fetchSymbol(",")
                self.compileType()
                self.compileVarName(self.subroutineVarList)
        self.end("parameterList")

    def compileSubroutineBody(self):
        self.begin("subroutineBody")
        self.fetchSymbol("{")
        while self.view().value == "var":
            self.compileVarDec()
        self.compileStatements()
        self.fetchSymbol("}")
        self.end("subroutineBody")

    def compileVarDec(self):
        self.begin("varDec")
        self.fetchToken("KEYWORD", "var")
        self.compileType()
        self.compileVarName(self.subroutineVarList)
        while self.view().value == ",":
            self.fetchSymbol(",")
            self.compileVarName(self.subroutineVarList)
        self.fetchSymbol(";")
        self.end("varDec")

    def compileClassName(self):
        self.begin("className")
        self.fetchToken("IDENTIFIER")
        self.end("className")

    def compileSubroutineName(self):
        self.begin("subroutineName")
        self.fetchToken("IDENTIFIER")
        self.end("subroutineName")

    def compileVarName(self, append=None):
        self.begin("varName")
        if append is not None:
            append.add(self.view().value)
        self.fetchToken("IDENTIFIER")
        self.end("varName")

    def viewIsStatement(self):
        return self.view().value in ("let", "if", "do", "while", "return")

    def compileStatements(self):
        self.begin("statements")
        while self.viewIsStatement():
            self.compileStatement()
        self.end("statements")

    def compileStatement(self):
        self.begin("statement")
        st = self.view().value
        if st == "let":
            self.compileLetStatement()
        elif st == "if":
            self.compileIfStatement()
        elif st == "do":
            self.compileDoStatement()
        elif st == "while":
            self.compileWhileStatement()
        elif st == "return":
            self.compileReturnStatement()
        else:
            raise SyntaxError("Kernel Fault")

        self.end("statement")

    def compileLetStatement(self):
        self.begin("letStatement")
        self.fetchToken("KEYWORD", "let")
        self.compileVarName()
        if self.view().value == "[":
            self.fetchSymbol("[")
            self.compileExpression()
            self.fetchSymbol("]")
        self.fetchSymbol("=")
        self.compileExpression()
        self.fetchSymbol(";")
        self.end("letStatement")

    def compileIfStatement(self):
        self.begin("ifStatement")
        self.fetchToken("KEYWORD", "if")
        self.fetchSymbol("(")
        self.compileExpression()
        self.fetchSymbol(")")
        self.fetchSymbol("{")
        self.compileStatements()
        self.fetchSymbol("}")
        if self.view().value == "else":
            self.fetchToken("KEYWORD", "else")
            self.compileStatements()
        self.end("ifStatement")

    def compileWhileStatement(self):
        self.begin("whileStatement")
        self.fetchToken("KEYWORD", "while")
        self.fetchSymbol("(")
        self.compileExpression()
        self.fetchSymbol(")")
        self.fetchSymbol("{")
        self.compileStatements()
        self.fetchSymbol("}")
        self.end("whileStatement")

    def compileDoStatement(self):
        self.begin("doStatement")
        self.fetchToken("KEYWORD", "do")
        self.compileSubroutineCall()
        self.fetchSymbol(";")
        self.end("doStatement")

    def compileReturnStatement(self):
        self.begin("returnStatement")
        self.fetchToken("KEYWORD", "return")
        if self.view().value != ";":
            self.compileExpression()
        self.fetchSymbol(";")
        self.end("returnStatement")

    def compileExpression(self):
        self.begin("expression")
        self.compileTerm()
        if self.viewIsOp():
            self.compileOp()
            self.compileTerm()
        self.end("expression")

    def compileTerm(self):
        self.begin("term")

        x = self.fetch()
        y = self.view()
        self.tokenizer.feedback(x)
        if x.value == '(':
            self.fetchSymbol('(')
            self.compileExpression()
            self.fetchSymbol(')')
        elif x.typ == "INT_CONST":
            self.fetchToken("INT_CONST")
        elif x.typ == "STRING_CONST":
            self.fetchToken("STRING_CONST")
        elif x.value in ("true", "false", "null", "this"):
            self.compileKeywordConstant()
        elif x.typ == "IDENTIFIER":
            if y.value == "[":
                self.compileVarName()
                self.fetchSymbol("[")
                self.compileExpression()
                self.fetchSymbol("]")
            elif y.value == "(" or y.value == '.':
                self.compileSubroutineCall()
            else:
                self.compileVarName()
        elif y.value == "(" or y.value == ".":
            self.fetchSymbol("(")
            self.compileExpression()
            self.fetchSymbol(")")
        elif x.value in "-~":
            self.compileUnaryOp()
            self.compileTerm()
        else:
            self.syntaxError(y.pos)

        self.end("term")

    def compileSubroutineCall(self):
        self.begin("subroutineCall")
        x = self.view()
        if x in self.classVarList or x in self.subroutineVarList:
            self.compileVarName()
            self.fetchSymbol(".")
            self.compileSubroutineName()
            self.fetchSymbol("(")
            self.compileExpressionList()
            self.fetchSymbol(")")
        else:
            x = self.fetch()
            y = self.view()
            self.tokenizer.feedback(x)
            if y.value == "(":
                self.compileSubroutineName()
                self.fetchSymbol("(")
                self.compileExpressionList()
                self.fetchSymbol(")")
            else:
                self.compileClassName()
                self.fetchSymbol(".")
                self.compileSubroutineName()
                self.fetchSymbol("(")
                self.compileExpressionList()
                self.fetchSymbol(")")
        self.end("subroutineCall")

    def compileExpressionList(self):
        self.begin("expressionList")
        x = self.view()
        if x.value != ")":
            self.compileExpression()
            while True:
                x = self.view()
                if x.value == ",":
                    self.fetchSymbol(",")
                    self.compileExpression()
                else:
                    break
        self.end("expressionList")

    def compileOp(self):
        self.begin("op")
        if self.viewIsOp():
            self.fetchToken("SYMBOL")
        else:
            self.syntaxError(self.view().pos)
        self.end("op")

    def compileUnaryOp(self):
        self.begin("unaryOp")
        if self.viewIsUnaryOp():
            self.fetchToken("SYMBOL")
        else:
            self.syntaxError(self.view().pos)
        self.end("unaryOp")

    def compileKeywordConstant(self):
        self.begin("keywordConstant")
        if self.view().value in ("true", "false", "null", "this"):
            self.fetchToken("KEYWORD")
        else:
            self.syntaxError(self.view().pos)
        self.end("keywordConstant")


if __name__ == "__main__":
    """tok = JackTokenizer("./Square/Square.jack")
    while tok.hasMoreTokens():
        x = tok.viewNext()
        print(tok.viewNext())
        if random.randint(0,4) == 0:
            tok.feedback(x)
        print(tok.advance())"""
    eng = CompilationEngine("./Square/Square.jack", "./Square/Square.xml")
    eng.compileClass()
