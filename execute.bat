@echo off
setlocal
rem スクリプトが置かれている場所をカレントディレクトリにする
cd /d %~dp0

SET APP_TITLE=folder_watch
SET EXE_SCRIPT=folder_watch.py
rem 監視フォルダ
SET WATCH_PATH=.\test\from
rem コピー先フォルダ
SET COPY_PATH=.\test\to
rem バックアップ先フォルダ
SET BK_PATH=.\test\bk
rem PID書き込みフォルダ
SET PID_FILD=pid

rem pidファイルあるかどうか確認 なければすぐに実行
IF EXIST %PID_FILD% (GOTO FILE_TRUE) ELSE GOTO FILE_FALSE

rem pidファイルが既にある場合
:FILE_TRUE

rem ファイルからpid番号取得
SET /p PID_VAL=<pid
rem pid存在フラグ(true=1, false=0)
SET IS_EXIST=0
rem イメージ名:"python.exe"とついたpidを検索する(数字部分のみ)
for /F "usebackq tokens=2" %%a in (
`tasklist /fi "IMAGENAME eq python.exe" ^| findstr "[0-9]"`) do (
rem ECHO %%a
if %%a==%PID_VAL% SET IS_EXIST=1
)
rem ECHO %PID_VAL%
rem ECHO %IS_EXIST%

rem 一致するものがある=既に起動状態なので何もしない
rem 一致するものがない=起動していないのでスクリプト実行
IF %IS_EXIST%==1 (GOTO EOF) ELSE (GOTO APPT_START) 

rem pidファイルがない場合
:FILE_FALSE
GOTO APPT_START

rem フォルダ監視実行
:APPT_START
START "%APP_TITLE%" ./python-3.8.2-embed-amd64/python.exe %EXE_SCRIPT% -w %WATCH_PATH% -cp %COPY_PATH% -bk %BK_PATH%
GOTO EOF


rem 終了
:EOF
rem pause
