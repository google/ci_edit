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
use super::buffer_manager::BufferManager;
use super::color::Colors;
use super::prefs::Prefs;
use std::cmp::min;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, RwLock};

extern crate ncurses; // https://crates.io/crates/ncurses

const KEY_CTRL_Q: i32 = 17;

// Helper function to initialize an MEVENT. (Is there a better approach?)
pub fn newMevent() -> ncurses::ll::MEVENT {
    ncurses::ll::MEVENT {
        id: 0,
        x: 0,
        y: 0,
        z: 0,
        bstate: 0,
    }
}

// A few helpful pieces of data to display in the debug window.
pub struct DebugInfo {
    mouse_event: ncurses::ll::MEVENT,
    pub ch: i32,
}

impl DebugInfo {
    pub fn new() -> DebugInfo {
        DebugInfo {
            mouse_event: newMevent(),
            ch: 0,
        }
    }
}

// This is the overall program singleton that holds the other important
// singletons such as the buffer_manager, preferences, and UI display.
pub struct CiProgram {
    buffer_manager: Mutex<BufferManager>,
    color: RwLock<Colors>,
    prefs: RwLock<Prefs>,
    exiting: AtomicBool,
    curses_screen: ncurses::WINDOW,
    pub debug_info: Mutex<DebugInfo>,
}

impl CiProgram {
    pub fn new() -> Arc<CiProgram> {
        let prefs = Prefs::new();
        let program = Arc::new(CiProgram {
            buffer_manager: Mutex::new(BufferManager::new()),
            color: RwLock::new(Colors::new(prefs.color256.clone())),
            prefs: RwLock::new(prefs),
            debug_info: Mutex::new(DebugInfo::new()),
            exiting: AtomicBool::new(false),
            curses_screen: ncurses::initscr(),
        });
        program
    }

    pub fn init(&self) {
        // Maybe set to "en_US.UTF-8"?
        ncurses::setlocale(ncurses::LcCategory::all, "");

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
        let mut mouse_event = newMevent();
        while self.exiting.load(Ordering::SeqCst) == false {
            let c = ncurses::getch();
            if c == 409 {
                let _err = ncurses::getmouse(&mut mouse_event);
            }
            {
                let mut info = self.debug_info.lock().unwrap();
                info.ch = c;
                info.mouse_event = mouse_event;
            }
            if c == KEY_CTRL_Q {
                self.quit_now();
            }
            if c >= 0 {
                // This grabs the mutex separately because this code will be in
                // a separate thread later (and I'm getting the hang of rust
                // mutex).
                let info = self.debug_info.lock().unwrap();
                ncurses::printw(&format!("pressed {}\n", info.ch));
                if c == 409 {
                    ncurses::printw(&format!("mouse {:?}\n", info.mouse_event));
                }
            }
        }
        ncurses::endwin();
    }

    pub fn parse_args(&self) {
        let debugRedo = false;
        let showLogWindow = false;
        let cliFiles: Vec<String>;
        //let cliFiles = vec![];
        let openToLine: Option<i32> = None;
        let profile = false;
        let readStdin = false;
        let takeAll = false; // Take all args as file paths.
        let timeStartup = false;
        let numColors = min(ncurses::COLORS(), 256);
        println!("{:?}", self.prefs);
        if std::env::var("CI_EDIT_SINGLE_THREAD").is_ok() {
            self.prefs
                .write()
                .unwrap()
                .editor
                .insert("useBgThread".to_string(), "false".to_string());
        }
    }

    pub fn quit_now(&self) {
        self.exiting.store(true, Ordering::SeqCst);
    }

    pub fn run(&self) {
        self.init();

        self.parse_args();
        self.set_up_palette();
        self.command_loop();
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
