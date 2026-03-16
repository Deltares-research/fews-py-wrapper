@ECHO OFF

set SPHINXBUILD=sphinx-build
set SOURCEDIR=.
set BUILDDIR=_build

IF "%1"=="" GOTO help

%SPHINXBUILD% -b %1% %SOURCEDIR% %BUILDDIR%\%1
GOTO end

:help
ECHO Usage: docs\make.bat [builder]
ECHO Example: docs\make.bat html

:end
