----                          
D:\ICICI-NRI-AC\AQ100\AICourse
.\Ai\Scripts\Activate.ps1

GIT
git init


Whenever you modify or add code:
git status
git add .
git commit -m "RAG with stremlit UI DEMO "
git push origin master

To download changes from GitHub
Before starting work, especially when working from another computer:

git pull origin master

Recommended daily workflow
git pull origin master
Make your code changes

git status
git add .
git commit -m "Streamlit APP"
git push origin master

Useful commands

Check current branch:

git branch

Check connected GitHub repository:

git remote -v

View commit history:

git log --oneline

Undo files added with git add . before committing:

git restore --staged .

Since your repository currently uses master, continue using:

git push origin master

Do not use git push origin main unless you rename the branch to main.