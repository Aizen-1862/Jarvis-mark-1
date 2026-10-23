using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
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

    private static void Launch(string app)
    {
        ProcessStartInfo start = new ProcessStartInfo();
        start.UseShellExecute = true;

        switch (app)
        {
            case "calculator":
                start.FileName = "explorer.exe";
                start.Arguments = @"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App";
                break;
            case "notepad":
                start.FileName = "notepad.exe";
                break;
            case "file explorer":
                start.FileName = "explorer.exe";
                break;
            case "paint":
                start.FileName = "mspaint.exe";
                break;
            case "spotify":
                start.FileName = "spotify:";
                break;
            default:
                throw new InvalidOperationException("App is not in the Windows launcher allowlist.");
        }

        Process.Start(start);
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
            Launch(app);
            Respond(new Dictionary<string, object> { { "ok", true }, { "launched", app } });
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
