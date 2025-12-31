import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'app.dart';

Future<void> main() async {
  // Ensure Flutter bindings are initialized
  WidgetsFlutterBinding.ensureInitialized();

  // Set preferred orientations
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Set system UI overlay style
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
      systemNavigationBarColor: Colors.black,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  // Initialize Hive for local storage
  await Hive.initFlutter();
  
  // Register Hive adapters here
  // Hive.registerAdapter(UserAdapter());
  // Hive.registerAdapter(PostAdapter());
  
  // Open Hive boxes
  // await Hive.openBox<User>('users');
  // await Hive.openBox<Post>('posts');
  // await Hive.openBox('settings');

  // Run the app with ProviderScope
  runApp(
    const ProviderScope(
      child: SWESphereApp(),
    ),
  );
}

