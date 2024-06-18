<openSSL 설치>  
Win32OpenSSL-3_3_1.exe

<anaconda 32bit 설치>  
  Anaconda3-2024.02-1-Windows-x86_64.exe

<환경 확인>  
	conda list (패키지 설치 목록 전체 확인)    
	conda list | findstr anaconda
 
<가상환경 생성>  
	[anaconda Prompt]  
	conda --version  
	conda info --envs  
	set CONDA_FORCE_32bit=1  
	conda create -n system_trading_py38_32 python=3.8  

<가상환경 삭제>  
	[anaconda Prompt]  
	conda info --envs  
	conda env list  
	conda remove --name 가상 환경 이름 --all  
	ex) conda remove --name py36_win32 --all  

<코드 라인 확대 축소>  
File -> Settings -> Editor -> General -> Code Folding > always  
	
