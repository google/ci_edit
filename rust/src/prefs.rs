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

type PrefMap = HashMap<String, String>;

pub struct Prefs {
    prefsDirectory: String,
    color8: PrefMap,
    color16: PrefMap,
    color256: PrefMap,
    color: Option<PrefMap>,
    //color: Option<&'a PrefMap>,
    editor: PrefMap,
    dev_test: PrefMap,
    palette: PrefMap,
    startup: PrefMap,
    status: PrefMap,
    user_data: PrefMap,
}

impl Prefs {
    pub fn new() -> Prefs {
        Prefs {
            prefsDirectory: "~/.ci_edit/prefs/".to_string(),
            color8: PrefMap::new(),
            color16: PrefMap::new(),
            color256: PrefMap::new(),
            color: None,
            editor: PrefMap::new(),
            dev_test: PrefMap::new(),
            palette: PrefMap::new(),
            startup: PrefMap::new(),
            status: PrefMap::new(),
            user_data: PrefMap::new(),
        }
    }
}
