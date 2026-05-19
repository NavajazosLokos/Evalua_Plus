import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class EvaluacionService {
  static const String baseUrl = '/api';

  // ── Preprocesar imagen (recorte + filtros) ─────────────────────────────────
  // Llama al servicio IA directamente (no pasa por el backend)
  static const String aiUrl = '/ia';

  static Future<Map<String, dynamic>> preprocesarImagen({
    required Uint8List imagenBytes,
    required String nombreArchivo,
  }) async {
    try {
      final uri     = Uri.parse('$aiUrl/preprocesar');
      final request = http.MultipartRequest('POST', uri);

      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          imagenBytes,
          filename: nombreArchivo,
        ),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success':        true,
          'imagen_base64':  data['imagen_base64'],
          'recorte_aplicado': data['recorte_aplicado'] ?? false,
        };
      } else {
        return {'success': false, 'message': 'Error al preprocesar imagen.'};
      }
    } catch (e) {
      // Si el servicio IA no está disponible, devolver la imagen original
      return {'success': false, 'message': 'Servicio IA no disponible.'};
    }
  }

  // ── Analizar imagen ────────────────────────────────────────────────────────
  static Future<Map<String, dynamic>> analizarImagen({
    required Uint8List imagenBytes,
    required String nombreArchivo,
  }) async {
    final token = await AuthService.getToken();
    if (token == null) {
      return {'success': false, 'message': 'No hay sesión activa.'};
    }

    final uri     = Uri.parse('$baseUrl/evaluaciones/analizar');
    final request = http.MultipartRequest('POST', uri);

    request.headers['Authorization'] = 'Bearer $token';
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        imagenBytes,
        filename: nombreArchivo,
      ),
    );

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return {'success': true, 'data': jsonDecode(response.body)};
      } else if (response.statusCode == 401) {
        return {'success': false, 'message': 'Sesión expirada. Inicia sesión de nuevo.'};
      } else {
        final error = jsonDecode(response.body);
        return {'success': false, 'message': error['detail'] ?? 'Error al analizar.'};
      }
    } catch (e) {
      return {'success': false, 'message': 'No se pudo conectar con el servidor.'};
    }
  }

  // ── Historial ──────────────────────────────────────────────────────────────
  static Future<Map<String, dynamic>> obtenerHistorial() async {
    final token = await AuthService.getToken();
    if (token == null) {
      return {'success': false, 'message': 'No hay sesión activa.'};
    }

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/evaluaciones/historial'),
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        return {'success': true, 'data': jsonDecode(response.body)};
      } else {
        return {'success': false, 'message': 'Error al obtener historial.'};
      }
    } catch (e) {
      return {'success': false, 'message': 'No se pudo conectar con el servidor.'};
    }
  }
}