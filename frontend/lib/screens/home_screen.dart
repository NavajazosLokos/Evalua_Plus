import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../services/auth_service.dart';
import '../services/evaluacion_service.dart';
import 'dart:html' as html;

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Uint8List? _imagenBytes;
  String? _nombreArchivo;
  bool _analizando = false;
  Map<String, dynamic>? _resultado;

  // ── Seleccionar imagen desde el navegador ──────────────────────────────────
  Future<void> _seleccionarImagen() async {
    final uploadInput = html.FileUploadInputElement()..accept = 'image/*';
    uploadInput.click();

    uploadInput.onChange.listen((event) async {
      final file = uploadInput.files?.first;
      if (file == null) return;

      final reader = html.FileReader();
      reader.readAsArrayBuffer(file);
      reader.onLoadEnd.listen((_) {
        setState(() {
          _imagenBytes = reader.result as Uint8List;
          _nombreArchivo = file.name;
          _resultado = null;
        });
      });
    });
  }

  // ── Enviar imagen al backend ───────────────────────────────────────────────
  Future<void> _analizar() async {
    if (_imagenBytes == null || _nombreArchivo == null) return;

    setState(() => _analizando = true);

    final respuesta = await EvaluacionService.analizarImagen(
      imagenBytes: _imagenBytes!,
      nombreArchivo: _nombreArchivo!,
    );

    setState(() {
      _analizando = false;
      if (respuesta['success']) {
        _resultado = respuesta['data'];
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(respuesta['message']),
            backgroundColor: Colors.red,
          ),
        );
      }
    });
  }

  Future<void> _cerrarSesion() async {
    await AuthService.logout();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/login');
  }

  // ── Color según estado ─────────────────────────────────────────────────────
  Color _colorEstado(String? estado) {
    switch (estado) {
      case 'Excelente':
        return const Color(0xFF16A34A);
      case 'Aceptable':
        return const Color(0xFFD97706);
      case 'Deteriorado':
        return const Color(0xFFDC2626);
      default:
        return Colors.grey;
    }
  }

  IconData _iconoEstado(String? estado) {
    switch (estado) {
      case 'Excelente':
        return Icons.check_circle_outline;
      case 'Aceptable':
        return Icons.warning_amber_outlined;
      case 'Deteriorado':
        return Icons.cancel_outlined;
      default:
        return Icons.help_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        backgroundColor: const Color(0xFF2563EB),
        foregroundColor: Colors.white,
        title: const Row(
          children: [
            Icon(Icons.analytics_outlined),
            SizedBox(width: 8),
            Text('EvaluaPlus', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Cerrar sesión',
            onPressed: _cerrarSesion,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // ── Título ───────────────────────────────────────────────────
                const Text(
                  'Analizar material',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Sube una imagen del material para evaluar su estado.',
                  style: TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 24),

                // ── Zona de carga de imagen ──────────────────────────────────
                GestureDetector(
                  onTap: _seleccionarImagen,
                  child: Container(
                    height: 260,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: _imagenBytes != null
                            ? const Color(0xFF2563EB)
                            : const Color(0xFFE2E8F0),
                        width: 2,
                      ),
                    ),
                    child: _imagenBytes != null
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(14),
                            child: Image.memory(_imagenBytes!, fit: BoxFit.cover),
                          )
                        : const Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.cloud_upload_outlined, size: 48, color: Color(0xFF2563EB)),
                              SizedBox(height: 12),
                              Text(
                                'Haz clic para seleccionar una imagen',
                                style: TextStyle(color: Colors.grey, fontSize: 15),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'PNG, JPG, JPEG',
                                style: TextStyle(color: Color(0xFFCBD5E1), fontSize: 13),
                              ),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 16),

                // ── Botones ──────────────────────────────────────────────────
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _seleccionarImagen,
                        icon: const Icon(Icons.image_outlined),
                        label: const Text('Cambiar imagen'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: (_imagenBytes == null || _analizando) ? null : _analizar,
                        icon: _analizando
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.search),
                        label: Text(_analizando ? 'Analizando...' : 'Analizar'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2563EB),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),

                // ── Resultado ────────────────────────────────────────────────
                if (_resultado != null) ...[
                  const Divider(),
                  const SizedBox(height: 20),
                  const Text(
                    'Resultado del análisis',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          // Estado
                          Icon(
                            _iconoEstado(_resultado!['resultado']?['estado']),
                            size: 52,
                            color: _colorEstado(_resultado!['resultado']?['estado']),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _resultado!['resultado']?['estado'] ?? 'Sin datos',
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                              color: _colorEstado(_resultado!['resultado']?['estado']),
                            ),
                          ),
                          const SizedBox(height: 16),
                          // Porcentaje
                          LinearProgressIndicator(
                            value: ((_resultado!['resultado']?['porcentaje_deterioro'] ?? 0) / 100),
                            backgroundColor: const Color(0xFFE2E8F0),
                            color: _colorEstado(_resultado!['resultado']?['estado']),
                            minHeight: 10,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${_resultado!['resultado']?['porcentaje_deterioro'] ?? 0}% de deterioro',
                            style: const TextStyle(color: Colors.grey),
                          ),
                          // Nota si hay
                          if (_resultado!['resultado']?['nota'] != null) ...[
                            const SizedBox(height: 16),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFFE2E8F0)),
                              ),
                              child: Text(
                                _resultado!['resultado']!['nota'],
                                style: const TextStyle(color: Colors.grey, fontSize: 13),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}