\# Reproducing the ARIS-N-ATLaS build



\## Prerequisites



\- Python 3.11+

\- Git

\- (Optional) A Kaggle account with GPU access for training

\- (Optional) A Hugging Face token with access to `NCAIR1/N-ATLaS`



\## Clone and install



```powershell

git clone https://github.com/Vicgrace01/aris-natlas.git

cd aris-natlas

python -m venv .venv

.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

