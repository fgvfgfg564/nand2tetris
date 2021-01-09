// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Put your code here.

@i
M = 0
@b
M = 1
@R2
M = 0

(LOOP)
	@R0
	D = M
	@b
	D = D&M
	@SKIP
	D;JEQ
	@R1
	D = M
	@R2
	M = D+M
	(SKIP)
	@b
	D = M
	M = D+M
	@R1
	D = M
	M = D+M
	@i
	MD = M+1
	@16
	D = D-A
	@LOOP
	D;JNE
