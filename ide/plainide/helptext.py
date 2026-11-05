"""The quick reference (Help > Quick reference, F1)."""

CHEAT_SHEET = """\
Variables        let health be 100          set health to health - 5
Output / input   say "Hello"                let name be input "Name?"
                 let age be input number "Age?"
Decisions        if x > 3 then ... else if ... then ... else ... end
Loops            repeat 3 times ... end     while x > 0 do ... end
                 for each item in items do ... end      stop / skip
Actions          action add takes(a, b) do  return a + b  end      run add(1, 2)   or   let n be add(1, 2)
                 action greet do ... end                           run greet()
Things           define Player as  x as number  end
                 let p be Player(x: 0)      say x of p
Lists            let l be list of number    add 5 to l     remove 5 from l
                 remove at 0 from l         sort l         size of l
                 l at 0                     set l at 0 to 7
                 contains(l, 5)
Text helpers     length of t   upper of t   lower of t
                 part(t, 0, 3)              contains(t, "a")
Number helpers   round of x    abs of x     sqrt of x
                 min(a, b)     max(a, b)    random(1, 6)
Windows          open window "Title" with width 640 and height 480
                 while window is open do ... show window ... end     close window
                 use color orange           use color 255, 128, 0    clear window with color black
                 draw rectangle at x, y size w by h      draw circle at x, y radius r
                 draw line from x1, y1 to x2, y2         draw text "hi" at x, y
                 key "left" is pressed      mouse x   mouse y   mouse is down
Colors           red green blue yellow orange purple pink brown gray white black
                 let sky be Color(red: 20, green: 24, blue: 40)    use color sky
Errors           try ... catch error then ... end
Comments         note: this is a comment

In the editor    F5 run, Shift+F5 stop, Ctrl+Space complete, Tab/Enter accept a suggestion
                 Ctrl+N new tab, Ctrl+W close tab, Ctrl+Tab next tab, Ctrl+O open, Ctrl+S save
                 Ctrl+P go to file, Ctrl+B show / hide the sidebar, Ctrl+Shift+E Explorer
                 'if', 'while', 'repeat', 'for', 'action', 'define' and 'try' fill in a whole block
Projects         Build (F6) makes a Python file, Release (F7) makes a program (exe) from it
                 File > New project / Open project / Open recent project; the first Save makes a project
Explorer         right click: New file, New folder, Rename (F2), Delete, Set as main program
                 click the .plainproject file to edit the project as text
Understanding    click a name to see where it is created and used (Ctrl+click jumps to where it is created)
                 'Live values' (next to Run) shows the values behind your code while the program runs; 'Value list' lists them
"""
