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
//use std::rc::{Rc, Weak};
//use std::cell::RefCell;
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicBool, Ordering};
use super::buffer_manager::BufferManager;

extern crate ncurses;

const KEY_CTRL_Q: i32 = 17;

pub struct CiProgram {
    buffer_manager: Mutex<BufferManager>,
    debug_mouse_event: Mutex<ncurses::ll::MEVENT>,
    exiting: AtomicBool,
    curses_screen: ncurses::WINDOW,
    ch: i32,
}

impl CiProgram {
    pub fn new() -> Arc<CiProgram> {
        let program = Arc::new(CiProgram {
            buffer_manager: Mutex::new(BufferManager::new()),
            debug_mouse_event: Mutex::new(ncurses::ll::MEVENT {
                id: 0,
                x: 0,
                y: 0,
                z: 0,
                bstate: 0,
            }),
            exiting: AtomicBool::new(false),
            curses_screen: ncurses::initscr(),
            ch: 0,
        });
        //*program.buffer_manager.borrow_mut().program.borrow_mut() = Rc::downgrade(&program);
        let mut guard = program.buffer_manager.lock().unwrap();
        guard.program = Some(program.clone());
        program.clone()
    }

    pub fn init(&self) {
        // Maybe set to "en_US.UTF-8"?
        ncurses::setlocale(ncurses::LcCategory::all, "");

        //let mut ci_program = CiProgram::new();
        ncurses::raw();
        ncurses::mousemask(ncurses::ALL_MOUSE_EVENTS as ncurses::mmask_t, None);
        ncurses::keypad(ncurses::stdscr(), true);
        ncurses::meta(ncurses::stdscr(), true);
        ncurses::noecho();
        enable_bracketed_paste().expect("enable_bracketed_paste failed");
        ncurses::start_color();
        ncurses::timeout(10);
        let curses_window = self.curses_screen;
        ncurses::leaveok(curses_window, true); // Don't update cursor position.
        ncurses::scrollok(curses_window, true);
        ncurses::keypad(curses_window, true);
        //app.window.mainCursesWindow = curses_window
    }

    pub fn command_loop(&self) {
        ncurses::clear();
        ncurses::mv(0, 0);
        ncurses::printw("This is a work in progress\n");
        ncurses::printw("Press ctrl+q to exit.\n");
        while self.exiting.load(Ordering::SeqCst) == false {
            let c = ncurses::getch();
            //self.ch = c;
            if c == KEY_CTRL_Q {
                self.quit_now();
            }
            if c == 409 {
                /*
                let _err = ncurses::getmouse(&mut self.debug_mouse_event.lock().unwrap());
                ncurses::printw(&format!(
                    "mouse {:?}\n",
                    self.debug_mouse_event
                ));
                */
            }
            if c >= 0 {
                ncurses::printw(&format!("pressed {}\n", self.ch));
            }
        }
        ncurses::endwin();
    }

    pub fn parse_args(&self) {}

    pub fn quit_now(&self) {
        self.exiting.store(true, Ordering::SeqCst);
    }

    pub fn run(&self) {
        self.init();

        self.parse_args();
        self.set_up_palette();
        /*
        homePath = app.prefs.prefs['userData'].get('homePath')
        self.makeHomeDirs(homePath)
        app.history.loadUserHistory()
        app.curses_util.hackCursesFixes()
        if app.prefs.editor['useBgThread']:
          self.bg = app.background.startupBackground()
        self.startup()
        if app.prefs.startup.get('profile'):
          profile = cProfile.Profile()
          profile.enable()
          self.commandLoop();
          profile.disable()
          output = io.StringIO.StringIO()
          stats = pstats.Stats(profile, stream=output).sort_stats('cumulative')
          stats.print_stats()
          app.log.info(output.getvalue())
        else:
        */
        self.command_loop();
        /*
        if app.prefs.editor['useBgThread']:
          self.bg.put((self.programWindow, 'quit'))
          self.bg.join()
        */
        ncurses::endwin();
    }

    pub fn set_up_palette(&self) {}
}

fn enable_bracketed_paste() -> std::io::Result<()> {
    // Enable Bracketed Paste Mode.
    let stdout = std::io::stdout();
    let mut stdout_handle = stdout.lock();
    stdout_handle.write(b"\033[?2004;h")?;
    // Push the escape codes out to the terminal. (Whether this is needed seems
    // to vary by platform).
    stdout_handle.flush()?;
    return Ok(());
}

pub fn run_ci() {
    // Reduce the delay waiting for escape sequences.
    std::env::set_var("ESCDELAY", "1");
    let ci_program = CiProgram::new();
    ci_program.run();
}
