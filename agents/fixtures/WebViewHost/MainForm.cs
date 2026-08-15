using System;
using System.IO;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;

namespace WebViewHost
{
    /// <summary>
    /// A native WinForms shell (UIA-visible controls) hosting an embedded Chromium
    /// browser (Edge WebView2) via the Core API directly on a Panel HWND — no
    /// WinForms-wrapper package needed. naturo dev/validation fixture: reproduces
    /// "native app window + embedded browser control showing a web page" with
    /// source we own, so every recognition technique (UIA shell, CDP web DOM,
    /// forced Chromium accessibility, injection) can be tried against known ground
    /// truth.
    ///
    ///   WebViewHost.exe            -> WebView2 with NO debug port (CDP-absent path)
    ///   WebViewHost.exe --cdp 9333 -> WebView2 with --remote-debugging-port=9333
    /// </summary>
    public class MainForm : Form
    {
        private readonly TextBox _url;
        private readonly Button _go;
        private readonly Label _status;
        private readonly Panel _host;
        private CoreWebView2Controller _controller;

        public MainForm()
        {
            Text = "Naturo WebView Host";
            Width = 900;
            Height = 720;

            _url = new TextBox { Left = 12, Top = 12, Width = 640, AccessibleName = "Address bar" };
            _go = new Button { Left = 664, Top = 10, Width = 90, Height = 26, Text = "Go", AccessibleName = "Go button" };
            _status = new Label { Left = 12, Top = 46, Width = 860, Height = 20, Text = "status: starting...", AccessibleName = "Status label" };
            _host = new Panel
            {
                Left = 12,
                Top = 72,
                Width = 860,
                Height = 600,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom,
            };

            Controls.Add(_url);
            Controls.Add(_go);
            Controls.Add(_status);
            Controls.Add(_host);

            _go.Click += (s, e) => { if (_controller != null) _controller.CoreWebView2.Navigate(_url.Text); };
            _host.SizeChanged += (s, e) => { if (_controller != null) _controller.Bounds = _host.ClientRectangle; };
            Load += async (s, e) => await InitAsync();
        }

        private async System.Threading.Tasks.Task InitAsync()
        {
            try
            {
                // Optional CDP debug port from `--cdp <port>`.
                string extraArgs = null;
                var args = Environment.GetCommandLineArgs();
                int i = Array.IndexOf(args, "--cdp");
                if (i >= 0 && i + 1 < args.Length)
                    extraArgs = "--remote-debugging-port=" + args[i + 1];

                var options = new CoreWebView2EnvironmentOptions(extraArgs);
                string udf = Path.Combine(Path.GetTempPath(), "NaturoWebViewHost");
                var env = await CoreWebView2Environment.CreateAsync(null, udf, options);
                _controller = await env.CreateCoreWebView2ControllerAsync(_host.Handle);
                _controller.Bounds = _host.ClientRectangle;

                string page = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "page.html");
                _url.Text = new Uri(page).AbsoluteUri;
                _controller.CoreWebView2.Navigate(_url.Text);

                int pid = (int)_controller.CoreWebView2.BrowserProcessId;
                _status.Text = "status: WebView2 ready. browserProcessId=" + pid +
                               ". cdpArgs=" + (extraArgs ?? "(none)");
                Text = "Naturo WebView Host - browserPID " + pid;
            }
            catch (Exception ex)
            {
                _status.Text = "status: WebView2 init FAILED: " + ex.Message;
            }
        }
    }
}
