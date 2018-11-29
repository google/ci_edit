// Copyright 2018 Google Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

use std::io::Write;

extern crate ncurses;

const KEY_CTRL_Q: i32 = 17;

struct CiProgram {
    debug_mouse_event: ncurses::ll::MEVENT,
    exiting: bool,
    curses_screen: ncurses::WINDOW,
    ch: i32,
}

impl CiProgram {
    pub fn new() -> CiProgram {
        CiProgram {
            debug_mouse_event: ncurses::ll::MEVENT {
                id: 0,
                x: 0,
                y: 0,
                z: 0,
                bstate: 0,
            },
            exiting: false,
            curses_screen: ncurses::initscr(),
            ch: 0,
        }
    }

    pub fn quit_now(&mut self) {
        self.exiting = true;
    }
}

pub fn enable_bracketed_paste() -> std::io::Result<()> {
    // Enable Bracketed Paste Mode.
    let stdout = std::io::stdout();
    let mut stdout_handle = stdout.lock();
    stdout_handle.write(b"\033[?2004;h")?;
    // Push the escape codes out to the terminal. (Whether this is needed seems
    // to vary by platform).
    stdout_handle.flush()?;
    return Ok(());
}

pub fn run() {
    // Maybe set to "en_US.UTF-8"?
    ncurses::setlocale(ncurses::LcCategory::all, "");

    let mut ci_program = CiProgram::new();
    ncurses::raw();
    ncurses::mousemask(ncurses::ALL_MOUSE_EVENTS as ncurses::mmask_t, None);
    ncurses::keypad(ncurses::stdscr(), true);
    ncurses::meta(ncurses::stdscr(), true);
    ncurses::noecho();
    enable_bracketed_paste().expect("enable_bracketed_paste failed");
    ncurses::start_color();
    ncurses::timeout(10);
    let curses_window = ci_program.curses_screen;
    ncurses::leaveok(curses_window, true); // Don't update cursor position.
    ncurses::scrollok(curses_window, true);
    ncurses::keypad(curses_window, true);
    //app.window.mainCursesWindow = curses_window

    ncurses::clear();
    ncurses::mv(0, 0);
    ncurses::printw("This is a work in progress\n");
    ncurses::printw("Press ctrl+q to exit.\n");
    while ci_program.exiting == false {
        let c = ncurses::getch();
        ci_program.ch = c;
        if c == KEY_CTRL_Q {
            ci_program.quit_now();
        }
        if c == 409 {
            let _err = ncurses::getmouse(&mut ci_program.debug_mouse_event);
            ncurses::printw(&format!("mouse {:?}\n", ci_program.debug_mouse_event));
        }
        if c >= 0 {
            ncurses::printw(&format!("pressed {}\n", ci_program.ch));
        }
    }
    ncurses::endwin();
}
