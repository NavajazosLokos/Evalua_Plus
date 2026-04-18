import 'package:flutter/material.dart';
import 'dart:typed_data';
import 'dart:html' as html;
import '../services/auth_service.dart';
import '../services/evaluacion_service.dart';

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
          SnackBar(content: Text(respuesta['message']), backgroundColor: Colors.red),
        );
      }
    });
  }

  Future<void> _cerrarSesion() async {
    await AuthService.logout();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/login');
  }

  Color _colorEstado(String? estado) {
    switch (estado) {
      case 'Excelente': return const Color(0xFF16A34A);
      case 'Aceptable': return const Color(0xFFD97706);
      case 'Deteriorado': return const Color(0xFFDC2626);
      default: return Colors.grey;
    }
  }

  String _emojiEstado(String? estado) {
    switch (estado) {
      case 'Excelente': return '✅';
      case 'Aceptable': return '⚠️';
      case 'Deteriorado': return '❌';
      default: return '❓';
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
            Text('📊', style: TextStyle(fontSize: 22)),
            SizedBox(width: 8),
            Text('EvaluaPlus', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          TextButton.icon(
            onPressed: _cerrarSesion,
            icon: const Text('🚪', style: TextStyle(fontSize: 18)),
            label: const Text('Salir', style: TextStyle(color: Colors.white)),
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
                const Text(
                  'Analizar material',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                ),
                const SizedBox(height: 4),
                const Text('Sube una imagen del material para evaluar su estado.', style: TextStyle(color: Colors.grey)),
                const SizedBox(height: 24),

                GestureDetector(
                  onTap: _seleccionarImagen,
                  child: Container(
                    height: 260,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: _imagenBytes != null ? const Color(0xFF2563EB) : const Color(0xFFE2E8F0),
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
                              Text('☁️', style: TextStyle(fontSize: 52)),
                              SizedBox(height: 12),
                              Text('Haz clic para seleccionar una imagen', style: TextStyle(color: Colors.grey, fontSize: 15)),
                              SizedBox(height: 4),
                              Text('PNG, JPG, JPEG', style: TextStyle(color: Color(0xFFCBD5E1), fontSize: 13)),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 16),

                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _seleccionarImagen,
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: const Text('🖼️  Cambiar imagen'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: (_imagenBytes == null || _analizando) ? null : _analizar,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2563EB),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: _analizando
                            ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Text('🔍  Analizar'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),

                if (_resultado != null) ...[
                  const Divider(),
                  const SizedBox(height: 20),
                  const Text('Resultado del análisis', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
                  const SizedBox(height: 16),
                  Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          Text(_emojiEstado(_resultado!['resultado']?['estado']), style: const TextStyle(fontSize: 52)),
                          const SizedBox(height: 8),
                          Text(
                            _resultado!['resultado']?['estado'] ?? 'Sin datos',
                            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: _colorEstado(_resultado!['resultado']?['estado'])),
                          ),
                          const SizedBox(height: 16),
                          LinearProgressIndicator(
                            value: ((_resultado!['resultado']?['porcentaje_deterioro'] ?? 0) / 100),
                            backgroundColor: const Color(0xFFE2E8F0),
                            color: _colorEstado(_resultado!['resultado']?['estado']),
                            minHeight: 10,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          const SizedBox(height: 8),
                          Text('${_resultado!['resultado']?['porcentaje_deterioro'] ?? 0}% de deterioro', style: const TextStyle(color: Colors.grey)),
                          if (_resultado!['resultado']?['nota'] != null) ...[
                            const SizedBox(height: 16),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFFE2E8F0)),
                              ),
                              child: Text(_resultado!['resultado']!['nota'], style: const TextStyle(color: Colors.grey, fontSize: 13), textAlign: TextAlign.center),
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