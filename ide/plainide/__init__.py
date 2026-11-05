"""The Plain IDE: a small editor for Plain programs, made for classrooms.

Layout of this package (each file has one job):

    paths, settings, crash     where files live, saved settings, crash reports
    theme, icons               colors, fonts and pictures
    language, helptext         what the editor knows about Plain
    editor, completer          one editor tab and its suggestion list
    tabstrip, documents        the row of tabs and the open files
    explorer, activitybar      the file tree and the bar with the view buttons
    output, values             the output panel and the list of values
    projects, projectui        project files (.plainproject) and the project menu actions
    running, building          Run (F5) and Build / Release (F6, F7)
    session                    crash handling, recovery of unsaved work
    menus, toolbar, statusbar, quickopen, dialogs
    app, main                  puts everything together
"""

TITLE = "Plain IDE"
VERSION = "0.3"
