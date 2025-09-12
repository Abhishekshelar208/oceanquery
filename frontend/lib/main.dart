import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'routes/app_router.dart';
import 'themes/app_theme.dart';
import 'services/api/api_client.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Load environment variables
  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    // .env file not found, using default values
    debugPrint('Environment file not found: $e');
  }
  
  // Initialize API client
  ApiClient().initialize();
  
  // TODO: Initialize Firebase
  // await Firebase.initializeApp(
  //   options: DefaultFirebaseOptions.currentPlatform,
  // );
  
  runApp(const OceanQueryApp());
}

class OceanQueryApp extends StatelessWidget {
  const OceanQueryApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'OceanQuery',
      debugShowCheckedModeBanner: false,
      
      // Theme configuration - Always light theme
      theme: AppTheme.lightTheme,
      themeMode: ThemeMode.light,
      
      // Router configuration
      routerConfig: AppRouter.router,
    );
  }
}
