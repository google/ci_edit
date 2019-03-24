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

//use std::io::Write;
use std::collections::HashMap;

pub type PrefMap = HashMap<String, String>;

#[derive(Debug)]
pub struct Prefs {
    pub prefs_directory: String,
    pub color8: PrefMap,
    pub color16: PrefMap,
    pub color256: PrefMap,
    //pub color: Option<PrefMap>,
    //color: Option<&'a PrefMap>,
    pub editor: PrefMap,
    pub dev_test: PrefMap,
    pub palette: PrefMap,
    pub startup: PrefMap,
    pub status: PrefMap,
    pub user_data: PrefMap,
}

impl Prefs {
    pub fn new() -> Prefs {
        Prefs {
            prefs_directory: "~/.ci_edit/prefs/".to_string(),
            color8: PrefMap::new(),
            color16: PrefMap::new(),
            color256: PrefMap::new(),
            //color: None,
            editor: PrefMap::new(),
            dev_test: PrefMap::new(),
            palette: PrefMap::new(),
            startup: PrefMap::new(),
            status: PrefMap::new(),
            user_data: PrefMap::new(),
        }
    }
}
