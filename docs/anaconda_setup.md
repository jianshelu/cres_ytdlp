# Using Anaconda3 with Antigravity

Antigravity uses the Python environment available in your terminal or selected in your IDE settings. Since you have Anaconda3 installed, you can configure Antigravity to use it.

## 1. Terminal Integration

When you open a terminal in Antigravity (or VS Code), it usually defaults to PowerShell or Command Prompt. To use Anaconda:

1.  **Initialize Conda for PowerShell:**
    Open your "Anaconda PowerShell Prompt" (from Start Menu) and run:
    ```powershell
    conda init powershell
    ```
    Restart Antigravity/VS Code. Now, when you open a terminal, it should detect Conda.

2.  **Activate Your Environment:**
    In the Antigravity terminal:
    ```powershell
    conda activate base
    # OR create a new one for this project
    conda create -n antigrav python=3.10 -y
    conda activate antigrav
    ```

## 2. Python Interpreter Selection

To ensure the Agent and IDE features (intellisense, linting) use Anaconda:

1.  Press `Ctrl+Shift+P` (Command Palette).
2.  Type **"Python: Select Interpreter"**.
3.  Choose your Anaconda environment (e.g., `Python 3.x (conda)` or path to `C:\Users\ruipe\anaconda3\python.exe`).

## 3. Verify

Run this in the Antigravity terminal to check which Python is active:
```bash
Get-Command python
# OR
python --version
```
It should verify it points to your Anaconda installation.
