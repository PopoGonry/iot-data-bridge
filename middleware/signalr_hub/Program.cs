using Microsoft.AspNetCore.SignalR;
using System.Collections.Concurrent;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container with performance optimizations
builder.Services.AddSignalR(options =>
{
    options.EnableDetailedErrors = false; // Disable in production
    options.MaximumReceiveMessageSize = 1024 * 1024; // 1MB max message size
    options.StreamBufferCapacity = 10;
    options.ClientTimeoutInterval = TimeSpan.FromSeconds(30);
    options.HandshakeTimeout = TimeSpan.FromSeconds(15);
    options.KeepAliveInterval = TimeSpan.FromSeconds(15);
});

// Add memory cache for connection management
builder.Services.AddMemoryCache();

// Optimized CORS policy
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader()
              .SetPreflightMaxAge(TimeSpan.FromHours(1)); // Cache preflight for 1 hour
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline with optimizations
app.UseCors("AllowAll");
app.UseRouting();

// Add compression for better performance
app.UseResponseCompression();

app.MapHub<IoTHub>("/hub");

app.MapGet("/", () => "IoT Data Bridge SignalR Hub is running!");
app.MapGet("/health", () => "OK");

// Configure to listen on all interfaces with optimized settings
app.Run("http://0.0.0.0:5000");

public class IoTHub : Hub
{
    private static readonly ConcurrentDictionary<string, DateTime> _connectionTimes = new();
    private static readonly ConcurrentDictionary<string, int> _messageCounts = new();
    private static int _totalConnections = 0;
    private static int _totalMessages = 0;

    public async Task JoinGroup(string groupName)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, groupName);
        _connectionTimes[Context.ConnectionId] = DateTime.UtcNow;
        Interlocked.Increment(ref _totalConnections);
        
        // Reduced logging for performance
        if (_totalConnections % 100 == 0)
        {
            Console.WriteLine($"Total connections: {_totalConnections}, Active: {_connectionTimes.Count}");
        }
    }

    public async Task LeaveGroup(string groupName)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, groupName);
        _connectionTimes.TryRemove(Context.ConnectionId, out _);
    }

    public async Task SendMessage(string groupName, string target, string message)
    {
        await Clients.Group(groupName).SendAsync(target, message);
        Interlocked.Increment(ref _totalMessages);
        
        // Batch logging for performance
        if (_totalMessages % 1000 == 0)
        {
            Console.WriteLine($"Total messages sent: {_totalMessages}");
        }
    }

    public async Task SendToGroup(string groupName, string target, object data)
    {
        await Clients.Group(groupName).SendAsync(target, data);
        Interlocked.Increment(ref _totalMessages);
    }

    public async Task SendBatchMessages(string groupName, string target, string batchMessagesJson)
    {
        try
        {
            // Optimized batch processing with parallel execution
            var batchMessages = JsonSerializer.Deserialize<object[]>(batchMessagesJson);
            
            if (batchMessages?.Length > 0)
            {
                // Send all messages in parallel for better performance
                var tasks = batchMessages.Select(message => 
                    Clients.Group(groupName).SendAsync(target, message));
                
                await Task.WhenAll(tasks);
                
                Interlocked.Add(ref _totalMessages, batchMessages.Length);
                
                // Reduced logging frequency
                if (_totalMessages % 5000 == 0)
                {
                    Console.WriteLine($"Batch sent {batchMessages.Length} messages to group {groupName}, Total: {_totalMessages}");
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error processing batch messages: {ex.Message}");
            throw;
        }
    }

    public override async Task OnConnectedAsync()
    {
        _connectionTimes[Context.ConnectionId] = DateTime.UtcNow;
        _messageCounts[Context.ConnectionId] = 0;
        
        // Reduced logging for performance
        if (_totalConnections % 50 == 0)
        {
            Console.WriteLine($"Client connected: {Context.ConnectionId} from {Context.GetHttpContext()?.Connection.RemoteIpAddress}");
        }
        
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _connectionTimes.TryRemove(Context.ConnectionId, out _);
        _messageCounts.TryRemove(Context.ConnectionId, out _);
        
        // Reduced logging for performance
        if (exception != null)
        {
            Console.WriteLine($"Client disconnected with error: {Context.ConnectionId}, Exception: {exception.Message}");
        }
        
        await base.OnDisconnectedAsync(exception);
    }

    // Performance monitoring methods
    public async Task GetStats()
    {
        var stats = new
        {
            TotalConnections = _totalConnections,
            ActiveConnections = _connectionTimes.Count,
            TotalMessages = _totalMessages,
            Uptime = DateTime.UtcNow - _connectionTimes.Values.DefaultIfEmpty(DateTime.UtcNow).Min()
        };
        
        await Clients.Caller.SendAsync("Stats", stats);
    }
}

