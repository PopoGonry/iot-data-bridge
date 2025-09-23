using Microsoft.AspNetCore.SignalR;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddSignalR(options =>
{
    options.EnableDetailedErrors = true;
    options.KeepAliveInterval = TimeSpan.FromSeconds(15);
    options.ClientTimeoutInterval = TimeSpan.FromSeconds(30);
    options.HandshakeTimeout = TimeSpan.FromSeconds(15);
});
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
        // Route messages from data_sources to iot_clients (middleware)
        if (groupName == "data_sources" && target == "ingress")
        {
            await Clients.Group("iot_clients").SendAsync("ingress", message);
            Console.WriteLine($"Routed from data_sources to iot_clients: {message}");
        }
        else
        {
            await Clients.Group(groupName).SendAsync(target, message);
            Console.WriteLine($"Sent to group {groupName}, target {target}: {message}");
        }
    }

    public async Task SendToGroup(string groupName, string target, object data)
    {
        await Clients.Group(groupName).SendAsync(target, data);
        Console.WriteLine($"Sent to group {groupName}, target {target}: {data}");
    }

<<<<<<< HEAD
<<<<<<< HEAD
    public async Task SendBatchMessages(string groupName, string target, string batchMessagesJson)
    {
        try
        {
            // 배치 메시지를 파싱하여 각각 전송
            var batchMessages = System.Text.Json.JsonSerializer.Deserialize<object[]>(batchMessagesJson);
            
            if (batchMessages == null || batchMessages.Length == 0)
            {
                Console.WriteLine("No messages in batch");
                return;
            }
            
            // Route batch messages from data_sources to iot_clients (middleware)
            if (groupName == "data_sources" && target == "ingress")
            {
                // Send each message individually to iot_clients group (Reference 방식)
                foreach (var message in batchMessages)
                {
                    await Clients.Group("iot_clients").SendAsync("ingress", message);
                }
                Console.WriteLine($"Routed {batchMessages.Length} batch messages from data_sources to iot_clients");
            }
            else
            {
                // Send each message individually to target group (Reference 방식)
                foreach (var message in batchMessages)
                {
                    await Clients.Group(groupName).SendAsync(target, message);
                }
                Console.WriteLine($"Sent {batchMessages.Length} batch messages to group {groupName}, target {target}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error processing batch messages: {ex.Message}");
            throw;
        }
    }

=======
>>>>>>> parent of de65d42 (perf: SignalR 데이터 전송 방식)
=======
>>>>>>> parent of de65d42 (perf: SignalR 데이터 전송 방식)
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

