// Copyright 2017 The ci_edit Authors. All rights reserved.
// Use of this source code is governed by an Apache-style license that can be
// found in the LICENSE file.

// This is a C++ sample file

#include "project_file.h"
#include <system_file.h>

// comment with \
a line continuation.

namespace sample {

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