using System;
using System.Diagnostics;
using System.IO;

class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        // 1. Locate project directory
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string projectDir = @"c:\Users\sameem\Desktop\Mark-XXXIX-OR-main\Mark-XXXIX-OR-main";
        
        // If main.py is in the same directory as this exe, use baseDir
        if (File.Exists(Path.Combine(baseDir, "main.py")))
        {
            projectDir = baseDir;
        }

        string scriptPath = Path.Combine(projectDir, "main.py");
        if (!File.Exists(scriptPath))
        {
            System.Windows.Forms.MessageBox.Show("Could not find LIHA main.py at:\n" + scriptPath, "LIHA Error", System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Error);
            return;
        }

        // 2. Locate Python executable
        string pythonExe = @"C:\Users\sameem\AppData\Local\Programs\Python\Python311\python.exe";
        if (!File.Exists(pythonExe))
        {
            pythonExe = "python.exe";
        }

        // 3. Launch LIHA
        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = pythonExe;
        psi.Arguments = "\"" + scriptPath + "\"";
        psi.WorkingDirectory = projectDir;
        psi.UseShellExecute = false;

        try
        {
            Process.Start(psi);
        }
        catch (Exception ex)
        {
            System.Windows.Forms.MessageBox.Show("Error launching LIHA:\n" + ex.Message, "LIHA Error", System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Error);
        }
    }
}
