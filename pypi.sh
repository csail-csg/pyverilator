#!/usr/bin/env bash

DIST=dist
PACKAGE=pyverilator-mm
PIP=pip3

function show_usage(){
    echo "Usage: $0 [OPTION]"
    echo " Available options:"
    echo " -h|--help     : Show help"
    echo " -c|--create   : Create local package"
    echo " -u            : Upload local package on test repository"
    echo " --upload      : Upload local package on pypi repository"
    echo " -i            : Install package from test repository"
    echo " --install     : Install package from pypi repository"
    echo " -un|--install : Uninstall package"
}

# if no argument is specified, show usage
if [[ "$#" -lt 1 ]]; 
then 
    show_usage
fi

## parse input args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help)       HELP=1;         shift ;;
        -c|--create)     CREATE=1;       shift ;;
        -u)              UPLOAD_TEST=1;  shift ;;
        --upload)        UPLOAD=1;       shift ;;
        -i)              INSTALL_TEST=1; shift ;;
        --install)       INSTALL=1;      shift ;;
        -un|--uninstall) UNINSTALL=1           ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [[ "$HELP" -gt 0 ]];
then
    show_usage
fi

if [[ "$CREATE" -gt 0 ]];
then
    echo "Creating new package... "
    rm -rf $DIST # remove old package folder
    python3 setup.py sdist # create package
fi

if [[ "$UPLOAD_TEST" -gt 0 ]];
then
    echo "Uploading package to testpypi... "
    twine upload --repository testpypi ${DIST}/* # upload to testpypi
fi

if [[ "$UPLOAD" -gt 0 ]];
then
    echo "Uploading package to pypi... "
    twine upload ${DIST}/* # upload to pypi
fi

if [[ "$UNINSTALL" -gt 0 || "$INSTALL" -gt 0 || "$INSTALL_TEST" -gt 0 ]];
then
    echo "Uninstalling package... "
    $PIP uninstall ${PACKAGE}
fi

if [[ "$INSTALL_TEST" -gt 0 ]];
then
    echo "Installing package from testpypi... "
    $PIP install --index-url https://test.pypi.org/simple/ ${PACKAGE}
fi

if [[ "$INSTALL" -gt 0 ]];
then
    echo "Installing package from pypi... "
    $PIP install ${PACKAGE}
fi