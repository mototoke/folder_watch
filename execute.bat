@echo off
setlocal
rem �X�N���v�g���u����Ă���ꏊ���J�����g�f�B���N�g���ɂ���
cd /d %~dp0

SET APP_TITLE=folder_watch
SET EXE_SCRIPT=folder_watch.py
rem �Ď��t�H���_
SET WATCH_PATH=.\test\from
rem �R�s�[��t�H���_
SET COPY_PATH=.\test\to
rem �o�b�N�A�b�v��t�H���_
SET BK_PATH=.\test\bk
rem PID�������݃t�H���_
SET PID_FILD=pid

rem pid�t�@�C�����邩�ǂ����m�F �Ȃ���΂����Ɏ��s
IF EXIST %PID_FILD% (GOTO FILE_TRUE) ELSE GOTO FILE_FALSE

rem pid�t�@�C�������ɂ���ꍇ
:FILE_TRUE

rem �t�@�C������pid�ԍ��擾
SET /p PID_VAL=<pid
rem pid���݃t���O(true=1, false=0)
SET IS_EXIST=0
rem �C���[�W��:"python.exe"�Ƃ���pid����������(���������̂�)
for /F "usebackq tokens=2" %%a in (
`tasklist /fi "IMAGENAME eq python.exe" ^| findstr "[0-9]"`) do (
rem ECHO %%a
if %%a==%PID_VAL% SET IS_EXIST=1
)
rem ECHO %PID_VAL%
rem ECHO %IS_EXIST%

rem ��v������̂�����=���ɋN����ԂȂ̂ŉ������Ȃ�
rem ��v������̂��Ȃ�=�N�����Ă��Ȃ��̂ŃX�N���v�g���s
IF %IS_EXIST%==1 (GOTO EOF) ELSE (GOTO APPT_START) 

rem pid�t�@�C�����Ȃ��ꍇ
:FILE_FALSE
GOTO APPT_START

rem �t�H���_�Ď����s
:APPT_START
START "%APP_TITLE%" ./python-3.8.2-embed-amd64/python.exe %EXE_SCRIPT% -w %WATCH_PATH% -cp %COPY_PATH% -bk %BK_PATH%
GOTO EOF


rem �I��
:EOF
rem pause
