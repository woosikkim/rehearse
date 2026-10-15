$ cd /app; ls -a . .rehearsal warriors; cat warriors/*.red
.:
.
..
.rehearsal
pmars-0.9.4
pmars_0.9.4-1.debian.tar.xz
pmars_0.9.4-1.dsc
pmars_0.9.4.orig.tar.xz
warriors
.rehearsal:
.
..
active
fixtures
scaffold
warriors:
.
..
g2-clear.red
paper.red
snake.red
stone.red
vampire.red
;redcode-94
;name G2-Clear
;author Unknown
;source https://corewar.co.uk/clear.htm
;strategy Simple clear loop with decrementing pointer
;assert CORESIZE == 8000 && MAXCYCLES == 80000
dec     equ     2700                ; Decrement value for bomb counter
gate    equ     clear-4             ; Gate location relative to clear
        org     clear-1             ; Start execution before clear
; Main data and bomb structures
bptr    dat     bomb,       9       ; Pointer to bomb with offset 9
bomb    spl     #dec,       11      ; Split with decrement value, creates processes
clear   mov     *bptr,      >gate   ; Move bomb contents through gate pointer
        mov     *bptr,      >gate   ; Second move for double clearing
        djn.f   clear,      }bomb   ; Decrement and jump if not zero (loop control)
        end
;redcode-94

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/stone.red | tail -2
Stone by mzvince (Everything2) scores 216
Results: 0 58 42

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/paper.red | tail -2
Paper by mzvince (Everything2) scores 100
Results: 0 0 100

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/vampire.red | tail -2
Vampire by mzvince (Everything2) scores 72
Results: 36 4 60

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/snake.red | tail -2
Snake by Wayne Sheppard scores 192
Results: 0 46 54

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/g2-clear.red | tail -2
G2-Clear by Unknown scores 206
Results: 0 53 47

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/stone.red | tail -1
Results: 51 49 0

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/paper.red | tail -1
Results: 98 1 1

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/vampire.red | tail -1
Results: 79 21 0

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/snake.red | tail -1
Results: 0 99 1

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/g2-clear.red | tail -1
Results: 12 87 1

$ cd /app; pmars -b -r 100 -f warriors/g2-clear.red warriors/snake.red | tail -1
Results: 50 44 6

$ cd /app; pmars -b -r 100 -f warriors/paper.red warriors/snake.red | tail -1
Results: 0 67 33

$ cd /app; pmars -b -r 100 -f warriors/g2-clear.red warriors/stone.red | tail -1
Results: 77 0 23

$ cd /app; pmars -b -r 100 -f warriors/g2-clear.red warriors/paper.red | tail -1
Results: 74 0 26

$ cd /app; pmars -b -r 100 -f warriors/g2-clear.red warriors/vampire.red | tail -1
Results: 84 7 9

$ cd /app; cp warriors/g2-clear.red my_warrior.red; pmars -b -r 100 -f my_warrior.red warriors/g2-clear.red | tail -1
Results: 47 53 0

$ cd /app; pmars -b -r 100 -f my_warrior.red warriors/snake.red | tail -1
Results: 50 44 6

