import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../../themes/app_theme.dart';
import '../../services/api/api_client.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  late final ApiClient _apiClient;
  // Always use Advanced Mode (RAG) - no toggle needed
  
  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient();
    _apiClient.initialize();
  }
  final List<ChatMessage> _messages = [
    ChatMessage(
      text: "🌊 **Welcome to Advanced Ocean AI!**\n\n🧠 I'm powered by **RAG** (Retrieval-Augmented Generation) with deep oceanographic knowledge.\n\n🚀 **What I can do:**\n• 📚 Provide scientific explanations\n• 🔬 Answer complex oceanographic questions\n• 📈 Query real ARGO float data\n• ⚡ Enhanced with Sentence Transformers\n\n**Try asking:**\n• \"Explain ocean salinity measurement\"\n• \"What is a thermocline?\"\n• \"How do ARGO floats work?\"\n• \"Show me temperature data near India\"",
      isUser: false,
      timestamp: DateTime.now().subtract(const Duration(minutes: 1)),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).dividerColor,
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.chat_bubble, color: AppTheme.primaryBlue),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          'Advanced Chatbot',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: AppTheme.primaryBlue,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.blue.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppTheme.primaryBlue, width: 1),
                          ),
                          child: const Text(
                            'RAG',
                            style: TextStyle(
                              color: AppTheme.primaryBlue,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    Text(
                      'Enhanced with oceanographic knowledge & context',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[700],
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _clearChat,
                  tooltip: 'Clear chat',
                ),
              ],
            ),
          ),
          
          // Messages
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                return _buildMessageBubble(_messages[index]);
              },
            ),
          ),
          
          // Input area
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                top: BorderSide(
                  color: Theme.of(context).dividerColor,
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Ask me anything about oceanography...',
                      hintStyle: TextStyle(color: Colors.grey[600]),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: AppTheme.lightBlue.withOpacity(0.5)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: const BorderSide(color: AppTheme.primaryBlue, width: 2),
                      ),
                      filled: true,
                      fillColor: AppTheme.surfaceBlue.withOpacity(0.5),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                    ),
                    maxLines: null,
                    textCapitalization: TextCapitalization.sentences,
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                FloatingActionButton(
                  onPressed: _sendMessage,
                  mini: true,
                  child: const Icon(Icons.send),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        mainAxisAlignment: message.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!message.isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: AppTheme.primaryBlue,
              child: const Icon(
                Icons.psychology,
                size: 16,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.7,
              ),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: message.isUser 
                    ? AppTheme.primaryBlue 
                    : AppTheme.surfaceBlue.withOpacity(0.7),
                borderRadius: BorderRadius.circular(16).copyWith(
                  topLeft: message.isUser ? const Radius.circular(16) : const Radius.circular(4),
                  topRight: message.isUser ? const Radius.circular(4) : const Radius.circular(16),
                ),
                border: message.isUser ? null : Border.all(
                  color: AppTheme.lightBlue.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  message.isUser 
                    ? Text(
                        message.text,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          height: 1.4,
                        ),
                      )
                    : MarkdownBody(
                        data: message.text,
                        styleSheet: MarkdownStyleSheet(
                          p: const TextStyle(
                            color: AppTheme.deepBlue,
                            fontSize: 14,
                            height: 1.4,
                          ),
                          h1: const TextStyle(
                            color: AppTheme.primaryBlue,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                          h2: const TextStyle(
                            color: AppTheme.primaryBlue,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                          strong: const TextStyle(
                            color: AppTheme.deepBlue,
                            fontWeight: FontWeight.bold,
                          ),
                          em: TextStyle(
                            color: Colors.grey[700],
                            fontStyle: FontStyle.italic,
                          ),
                          listBullet: const TextStyle(
                            color: AppTheme.primaryBlue,
                            fontSize: 14,
                          ),
                          code: TextStyle(
                            backgroundColor: AppTheme.surfaceBlue.withOpacity(0.5),
                            color: AppTheme.deepBlue,
                            fontSize: 13,
                            fontFamily: 'monospace',
                          ),
                        ),
                        selectable: true,
                      ),
                  const SizedBox(height: 4),
                  Text(
                    _formatTimestamp(message.timestamp),
                    style: TextStyle(
                      color: message.isUser ? Colors.white70 : Colors.grey[600],
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (message.isUser) ...[
            const SizedBox(width: 8),
            const CircleAvatar(
              radius: 16,
              backgroundColor: AppTheme.lightBlue,
              child: Icon(
                Icons.person,
                size: 16,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _sendMessage() {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add(ChatMessage(
        text: text,
        isUser: true,
        timestamp: DateTime.now(),
      ));
    });

    _messageController.clear();
    _sendRealAPIRequest(text);
  }

  Future<void> _sendRealAPIRequest(String userMessage) async {
    try {
      // Show advanced AI typing indicator
      setState(() {
        _messages.add(ChatMessage(
          text: "🧠 Analyzing with advanced AI & oceanographic knowledge...",
          isUser: false,
          timestamp: DateTime.now(),
        ));
      });
      
      // Always call advanced RAG API
      final response = await _apiClient.sendAdvancedChatMessage(userMessage);
      
      // Remove typing indicator
      setState(() {
        _messages.removeLast();
      });
      
      // Show real response
      String responseText = response['message'] ?? 'No response received';
      
      // Add SQL query if available
      if (response['sql_query'] != null) {
        responseText += '\n\n📝 **Generated SQL:**\n```sql\n${response['sql_query']}\n```';
      }
      
      // Add processing time
      if (response['processing_time_ms'] != null) {
        responseText += '\n\n⚡ Processed in ${response['processing_time_ms'].toStringAsFixed(1)}ms';
      }
      
      setState(() {
        _messages.add(ChatMessage(
          text: responseText,
          isUser: false,
          timestamp: DateTime.now(),
        ));
      });
      
    } catch (e) {
      // Remove typing indicator if error occurs
      setState(() {
        if (_messages.isNotEmpty && _messages.last.text.contains("Analyzing")) {
          _messages.removeLast();
        }
        _messages.add(ChatMessage(
          text: "❌ Sorry, I couldn't process your request: $e\n\nPlease try again or check if the backend is running.",
          isUser: false,
          timestamp: DateTime.now(),
        ));
      });
    }
  }


  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);
    
    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }

  void _clearChat() {
    setState(() {
      _messages.clear();
      _messages.add(ChatMessage(
        text: "Chat cleared. How can I help you explore ocean data?",
        isUser: false,
        timestamp: DateTime.now(),
      ));
    });
  }


  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }
}

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}
