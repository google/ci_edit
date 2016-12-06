// This is a C++ sample file

#include "project_file.h"
#include <system_file.h>

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
    std::out << "thing " << this.member_var_;
  }

 private:
  double member_var_;
};

}  // namespace sample