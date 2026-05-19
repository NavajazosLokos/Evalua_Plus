import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  // En desarrollo apunta al backend local
  static const String baseUrl = '/api';

  // ── Login ──────────────────────────────────────────────────────────────────
  static Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      body: {
        'username': email,
        'password': password,
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      // Guardar token localmente
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('token', data['access_token']);
      return {'success': true};
    } else {
      final error = jsonDecode(response.body);
      return {'success': false, 'message': error['detail'] ?? 'Error al iniciar sesión'};
    }
  }

  // ── Registro ───────────────────────────────────────────────────────────────
  static Future<Map<String, dynamic>> registro(String name, String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/registro'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name, 'email': email, 'password': password}),
    );

    if (response.statusCode == 201) {
      return {'success': true};
    } else {
      final error = jsonDecode(response.body);
      return {'success': false, 'message': error['detail'] ?? 'Error al registrarse'};
    }
  }

  // ── Cerrar sesión ──────────────────────────────────────────────────────────
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
  }

  // ── Obtener token guardado ─────────────────────────────────────────────────
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token');
  }

  // ── Verificar si está logueado ─────────────────────────────────────────────
  static Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }
}