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

use super::ci_program::CiProgram;
use super::prefs::Prefs;
use super::text_buffer::TextBuffer;
use std::sync::Arc;

pub struct BufferManager {
    pub program: Option<Arc<CiProgram>>,
    buffers: Vec<TextBuffer>,
}

impl BufferManager {
    //pub fn new(program: RefCell<Weak<CiProgram>>) -> BufferManager {
    pub fn new() -> BufferManager {
        BufferManager {
            program: None,
            //prefs: prefs::Prefs::new(),
            buffers: vec![],
        }
    }

    pub fn init(&mut self) {}

    pub fn set_up_palette(&mut self) {}
}
