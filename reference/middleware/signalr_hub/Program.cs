using Microsoft.AspNetCore.SignalR;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddSignalR();
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline.
app.UseCors("AllowAll");
app.UseRouting();

app.MapHub<IoTHub>("/hub");

app.MapGet("/", () => "IoT Data Bridge SignalR Hub is running!");

// Configure to listen on all interfaces (0.0.0.0) instead of just localhost
app.Run("http://0.0.0.0:5000");

public class IoTHub : Hub
{
    public async Task JoinGroup(string groupName)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, groupName);
        Console.WriteLine($"Client {Context.ConnectionId} joined group {groupName}");
    }

    public async Task LeaveGroup(string groupName)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, groupName);
        Console.WriteLine($"Client {Context.ConnectionId} left group {groupName}");
    }

    public async Task SendMessage(string groupName, string target, string message)
    {
        await Clients.Group(groupName).SendAsync(target, message);
        Console.WriteLine($"Sent to group {groupName}, target {target}: {message}");
    }

    public async Task SendToGroup(string groupName, string target, object data)
    {
        await Clients.Group(groupName).SendAsync(target, data);
        Console.WriteLine($"Sent to group {groupName}, target {target}: {data}");
    }

    public async Task SendBatchMessages(string groupName, string target, string batchMessagesJson)
    {
        try
        {
            // 배치 메시지를 파싱하여 각각 전송
            var batchMessages = System.Text.Json.JsonSerializer.Deserialize<object[]>(batchMessagesJson);
            
            foreach (var message in batchMessages)
            {
                await Clients.Group(groupName).SendAsync(target, message);
            }
            
            Console.WriteLine($"Sent {batchMessages.Length} batch messages to group {groupName}, target {target}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error processing batch messages: {ex.Message}");
            throw;
        }
    }

    public override async Task OnConnectedAsync()
    {
        Console.WriteLine($"Client connected: {Context.ConnectionId} from {Context.GetHttpContext()?.Connection.RemoteIpAddress}");
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        Console.WriteLine($"Client disconnected: {Context.ConnectionId}, Exception: {exception?.Message}");
        await base.OnDisconnectedAsync(exception);
    }
}

