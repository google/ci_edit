// Copyright 2017 Google Inc.
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

// This is a C++ sample file

#include "project_file.h"
#include <system_file.h>

// comment with \
a line continuation.

namespace sample {

#if defined(foo) && \
    defined(bar)
// a comment.
#endif


/**
 * A multi-line
 * comment.
 */
int GetInt(const char* string) {
  return 54;
}

class Sample
{
 public:
  Sample(double param): member_var_(param) {}

  void thing() {
    std::out << "thing 234\"32 (class) void" << " 'blah'." << this.member_var_;
  }

 private:
  double member_var_;
};

}  // namespace sample