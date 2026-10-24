using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;

internal static class JarvisNativeHost
{
    private const int MaxMessageBytes = 1024 * 1024;

    private static byte[] ReadExact(Stream input, int length)
    {
        byte[] result = new byte[length];
        int offset = 0;
        while (offset < length)
        {
            int count = input.Read(result, offset, length - offset);
            if (count == 0) throw new EndOfStreamException("Incomplete native message.");
            offset += count;
        }
        return result;
    }

    private static void Respond(object response)
    {
        byte[] body = Encoding.UTF8.GetBytes(new JavaScriptSerializer().Serialize(response));
        byte[] header = BitConverter.GetBytes(body.Length);
        Stream output = Console.OpenStandardOutput();
        output.Write(header, 0, header.Length);
        output.Write(body, 0, body.Length);
        output.Flush();
    }

    private static string Normalize(string value)
    {
        return new string((value ?? "").ToLowerInvariant().Where(Char.IsLetterOrDigit).ToArray());
    }

    private static void Start(string fileName, string arguments = "")
    {
        ProcessStartInfo start = new ProcessStartInfo();
        start.FileName = fileName;
        start.Arguments = arguments;
        start.UseShellExecute = true;
        Process.Start(start);
    }

    private static string FindStartMenuShortcut(string app)
    {
        string wanted = Normalize(app);
        string[] roots = new string[] {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), @"Microsoft\Windows\Start Menu\Programs"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), @"Microsoft\Windows\Start Menu\Programs")
        };
        List<string> matches = new List<string>();
        foreach (string root in roots)
        {
            if (!Directory.Exists(root)) continue;
            foreach (string path in Directory.GetFiles(root, "*.lnk", SearchOption.AllDirectories))
            {
                string name = Path.GetFileNameWithoutExtension(path);
                if (Normalize(name) == wanted) return path;
                if (wanted.Length >= 3 && Normalize(name).StartsWith(wanted, StringComparison.Ordinal)) matches.Add(path);
            }
        }
        if (matches.Count == 1) return matches[0];
        if (matches.Count > 1) throw new InvalidOperationException("More than one installed app matches that name. Say its full Start Menu name.");
        return null;
    }

    private static string FindPackagedAppId(string app)
    {
        // This fixed, read-only command enumerates Start Menu app names. The
        // requested app name is never inserted into a shell command.
        ProcessStartInfo info = new ProcessStartInfo();
        info.FileName = "powershell.exe";
        info.Arguments = "-NoProfile -NonInteractive -Command \"Get-StartApps | ForEach-Object { $_.Name + [char]9 + $_.AppID }\"";
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = false;
        using (Process process = Process.Start(info))
        {
            System.Threading.Tasks.Task<string> outputTask = process.StandardOutput.ReadToEndAsync();
            if (!process.WaitForExit(7000))
            {
                try { process.Kill(); } catch { }
                return null;
            }
            string output = outputTask.Result;
            string wanted = Normalize(app);
            List<string> matches = new List<string>();
            foreach (string line in output.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string[] fields = line.Split(new char[] { '\t' }, 2);
                if (fields.Length != 2) continue;
                if (Normalize(fields[0]) == wanted) return fields[1].Trim();
                if (wanted.Length >= 3 && Normalize(fields[0]).StartsWith(wanted, StringComparison.Ordinal)) matches.Add(fields[1].Trim());
            }
            if (matches.Count == 1) return matches[0];
            if (matches.Count > 1) throw new InvalidOperationException("More than one installed app matches that name. Say its full Start Menu name.");
        }
        return null;
    }

    private static void Launch(string app)
    {
        if (String.IsNullOrWhiteSpace(app) || app.Length > 100 || app.Any(c => !(Char.IsLetterOrDigit(c) || " .&()+_-".IndexOf(c) >= 0)))
            throw new InvalidOperationException("Give me an installed app's display name, not a command or file path.");

        string shortcut = FindStartMenuShortcut(app);
        if (shortcut != null)
        {
            Start(shortcut);
            return;
        }

        string appId = FindPackagedAppId(app);
        if (appId != null)
        {
            Start("explorer.exe", "shell:AppsFolder\\" + appId);
            return;
        }

        string normalized = Normalize(app);
        if (normalized == "fileexplorer") { Start("explorer.exe"); return; }
        if (normalized == "calculator") { Start("calc.exe"); return; }
        if (normalized == "notepad") { Start("notepad.exe"); return; }
        if (normalized == "paint") { Start("mspaint.exe"); return; }
        throw new InvalidOperationException("I couldn't find that app in this Windows account's Start Menu. Try its full app name.");
    }

    private static object SafeLaunch(string app)
    {
        Launch(app);
        return new Dictionary<string, object> { { "ok", true }, { "launched", app } };
    }

    private static void Main(string[] args)
    {
        try
        {
            Stream input = Console.OpenStandardInput();
            byte[] header = new byte[4];
            int first = input.Read(header, 0, header.Length);
            if (first == 0) return;
            if (first < header.Length)
            {
                byte[] remainder = ReadExact(input, header.Length - first);
                Buffer.BlockCopy(remainder, 0, header, first, remainder.Length);
            }

            int length = BitConverter.ToInt32(header, 0);
            if (length < 0 || length > MaxMessageBytes)
                throw new InvalidDataException("Native message size is invalid.");

            string json = Encoding.UTF8.GetString(ReadExact(input, length));
            Dictionary<string, object> message = new JavaScriptSerializer()
                .Deserialize<Dictionary<string, object>>(json);
            if (message == null || !Object.Equals(message.ContainsKey("action") ? message["action"] : null, "open_app"))
                throw new InvalidOperationException("Unsupported action.");

            string app = Convert.ToString(message.ContainsKey("app") ? message["app"] : null);
            Respond(SafeLaunch(app));
        }
        catch (Exception error)
        {
            Respond(new Dictionary<string, object> {
                { "ok", false },
                { "error", error.Message.Length > 300 ? error.Message.Substring(0, 300) : error.Message }
            });
        }
    }
}
