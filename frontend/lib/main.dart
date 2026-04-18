import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'services/auth_service.dart';

void main() {
  runApp(const EvaluaPlusApp());
}

class EvaluaPlusApp extends StatelessWidget {
  const EvaluaPlusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EvaluaPlus',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2563EB),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'Roboto',
        iconTheme: const IconThemeData(
          color: Color(0xFF64748B),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          iconColor: Color(0xFF64748B),
          prefixIconColor: Color(0xFF64748B),
          suffixIconColor: Color(0xFF64748B),
        ),
      ),
      home: const _SplashRouter(),
      routes: {
        '/login': (context) => const LoginScreen(),
        '/home': (context) => const HomeScreen(),
      },
    );
  }
}

class _SplashRouter extends StatefulWidget {
  const _SplashRouter();

  @override
  State<_SplashRouter> createState() => _SplashRouterState();
}

class _SplashRouterState extends State<_SplashRouter> {
  @override
  void initState() {
    super.initState();
    _redirigir();
  }

  Future<void> _redirigir() async {
    await Future.delayed(const Duration(milliseconds: 300));
    if (!mounted) return;

    final logueado = await AuthService.isLoggedIn();
    if (!mounted) return;

    if (logueado) {
      Navigator.pushReplacementNamed(context, '/home');
    } else {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}