
Please write test file for the following files.
* 1 test file per py file.
* Your tests should go under: $repo_root/tests/mirror/$same_file_path_relative_to_repo_root
* in your tests, you assume all types will be respected, so no need to experiment on that. In other words, you only test for things that the strict harsh static type analyzer is still not capable of catching, i.e. things that can only be determined at runtime. One example of these, if a file is reading another file, static type anaylzer dones't know that other config file being read exists, we only know at runtime. Especially if that config helper file should be withthin the repo itself, not passed by user, so it must exist otherwise the repo is broken out of the box. I hope this was clear enough.

