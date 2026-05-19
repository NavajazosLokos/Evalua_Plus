import 'package:flutter/material.dart';
import 'dart:typed_data';
import 'dart:html' as html;
import 'dart:convert';
import '../services/auth_service.dart';
import '../services/evaluacion_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Uint8List? _imagenMostradaBytes; // imagen recortada (la que ve el usuario y se analiza)
  String?    _nombreArchivo;
  bool       _analizando        = false;
  bool       _preprocesando     = false;
  bool       _cargandoHistorial = false;
  bool       _recorteAplicado   = false;
  Map<String, dynamic>? _resultado;
  List<dynamic> _historial = [];

  @override
  void initState() {
    super.initState();
    _cargarHistorial();
  }

  // ── Seleccionar imagen → preprocesar automáticamente ──────────────────────
  Future<void> _seleccionarImagen() async {
    final uploadInput = html.FileUploadInputElement()..accept = 'image/*';
    uploadInput.click();

    uploadInput.onChange.listen((event) async {
      final file = uploadInput.files?.first;
      if (file == null) return;

      final reader = html.FileReader();
      reader.readAsArrayBuffer(file);

      reader.onLoadEnd.listen((_) async {
        final bytes = reader.result as Uint8List;

        setState(() {
          _imagenMostradaBytes = bytes; // mostrar original mientras procesa
          _nombreArchivo       = file.name;
          _resultado           = null;
          _recorteAplicado     = false;
          _preprocesando       = true;
        });

        // Llamar a /preprocesar del servicio IA
        final resultado = await EvaluacionService.preprocesarImagen(
          imagenBytes:   bytes,
          nombreArchivo: file.name,
        );

        if (resultado['success'] && resultado['imagen_base64'] != null) {
          final imgBytes = base64Decode(resultado['imagen_base64'] as String);
          setState(() {
            _imagenMostradaBytes = imgBytes;
            _recorteAplicado     = resultado['recorte_aplicado'] ?? false;
            _preprocesando       = false;
          });
        } else {
          // Fallback: usar imagen original sin corte
          setState(() => _preprocesando = false);
        }
      });
    });
  }

  // ── Analizar la imagen ya procesada ───────────────────────────────────────
  Future<void> _analizar() async {
    if (_imagenMostradaBytes == null || _nombreArchivo == null) return;
    setState(() => _analizando = true);

    final respuesta = await EvaluacionService.analizarImagen(
      imagenBytes:   _imagenMostradaBytes!,
      nombreArchivo: _nombreArchivo!,
    );

    setState(() {
      _analizando = false;
      if (respuesta['success']) {
        _resultado = respuesta['data'];
        _cargarHistorial();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:         Text(respuesta['message']),
            backgroundColor: Colors.red,
          ),
        );
      }
    });
  }

  Future<void> _cargarHistorial() async {
    setState(() => _cargandoHistorial = true);
    final respuesta = await EvaluacionService.obtenerHistorial();
    setState(() {
      _cargandoHistorial = false;
      if (respuesta['success']) _historial = respuesta['data'] ?? [];
    });
  }

  Future<void> _cerrarSesion() async {
    await AuthService.logout();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/login');
  }

  // ── Helpers de UI ─────────────────────────────────────────────────────────
  Color _colorEstado(String? e) {
    switch (e) {
      case 'Excelente':   return const Color(0xFF16A34A);
      case 'Aceptable':   return const Color(0xFFD97706);
      case 'Deteriorado': return const Color(0xFFDC2626);
      default:            return Colors.grey;
    }
  }

  String _emojiEstado(String? e) {
    switch (e) {
      case 'Excelente':   return '✅';
      case 'Aceptable':   return '⚠️';
      case 'Deteriorado': return '❌';
      default:            return '❓';
    }
  }

  Color _colorStatus(String? s) {
    switch (s) {
      case 'completed': return const Color(0xFF16A34A);
      case 'pending':   return const Color(0xFFD97706);
      case 'error':     return const Color(0xFFDC2626);
      default:          return Colors.grey;
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
            icon:  const Text('🚪', style: TextStyle(fontSize: 18)),
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

                // ── Título ───────────────────────────────────────────────
                const Text('Analizar material',
                    style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E293B))),
                const SizedBox(height: 4),
                const Text(
                    'Sube una imagen del material para evaluar su estado.',
                    style: TextStyle(color: Colors.grey)),
                const SizedBox(height: 24),

                // ── Zona imagen ──────────────────────────────────────────
                GestureDetector(
                  onTap: _seleccionarImagen,
                  child: Container(
                    height: 280,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: _imagenMostradaBytes != null
                            ? const Color(0xFF2563EB)
                            : const Color(0xFFE2E8F0),
                        width: 2,
                      ),
                    ),
                    child: _preprocesando
                        ? const Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Color(0xFF2563EB)),
                              SizedBox(height: 14),
                              Text('Removiendo fondo...',
                                  style: TextStyle(
                                      color: Color(0xFF64748B),
                                      fontSize: 13)),
                            ],
                          )
                        : _imagenMostradaBytes != null
                            ? Stack(
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(14),
                                    child: Image.memory(
                                      _imagenMostradaBytes!,
                                      fit: BoxFit.contain,
                                      width: double.infinity,
                                      height: double.infinity,
                                    ),
                                  ),
                                  // Badge si se aplicó recorte
                                  if (_recorteAplicado)
                                    Positioned(
                                      top: 10,
                                      right: 10,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFF2563EB)
                                              .withOpacity(0.85),
                                          borderRadius:
                                              BorderRadius.circular(20),
                                        ),
                                        child: const Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Text('✂️',
                                                style:
                                                    TextStyle(fontSize: 11)),
                                            SizedBox(width: 4),
                                            Text('Fondo removido',
                                                style: TextStyle(
                                                    color: Colors.white,
                                                    fontSize: 11,
                                                    fontWeight:
                                                        FontWeight.w500)),
                                          ],
                                        ),
                                      ),
                                    ),
                                ],
                              )
                            : const Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text('☁️',
                                      style: TextStyle(fontSize: 52)),
                                  SizedBox(height: 12),
                                  Text(
                                      'Haz clic para seleccionar una imagen',
                                      style: TextStyle(
                                          color: Colors.grey,
                                          fontSize: 15)),
                                  SizedBox(height: 4),
                                  Text('PNG, JPG, JPEG',
                                      style: TextStyle(
                                          color: Color(0xFFCBD5E1),
                                          fontSize: 13)),
                                ],
                              ),
                  ),
                ),
                const SizedBox(height: 16),

                // ── Botones ──────────────────────────────────────────────
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _seleccionarImagen,
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                        child: const Text('🖼️  Cambiar imagen'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: (_imagenMostradaBytes == null ||
                                _analizando ||
                                _preprocesando)
                            ? null
                            : _analizar,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2563EB),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                        child: _analizando
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                    color: Colors.white, strokeWidth: 2))
                            : const Text('🔍  Analizar'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),

                // ── Resultado ────────────────────────────────────────────
                if (_resultado != null) ...[
                  const Divider(),
                  const SizedBox(height: 20),
                  const Text('Resultado del análisis',
                      style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1E293B))),
                  const SizedBox(height: 16),
                  Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14)),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          Text(
                              _emojiEstado(
                                  _resultado!['resultado']?['estado']),
                              style: const TextStyle(fontSize: 52)),
                          const SizedBox(height: 8),
                          Text(
                            _resultado!['resultado']?['estado'] ?? 'Sin datos',
                            style: TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: _colorEstado(
                                    _resultado!['resultado']?['estado'])),
                          ),
                          const SizedBox(height: 16),
                          LinearProgressIndicator(
                            value: ((_resultado!['resultado']
                                            ?['porcentaje_deterioro'] ??
                                        0) /
                                    100),
                            backgroundColor: const Color(0xFFE2E8F0),
                            color: _colorEstado(
                                _resultado!['resultado']?['estado']),
                            minHeight: 10,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          const SizedBox(height: 8),
                          Text(
                              '${_resultado!['resultado']?['porcentaje_deterioro'] ?? 0}% de deterioro',
                              style: const TextStyle(color: Colors.grey)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                ],

                // ── Historial ────────────────────────────────────────────
                const Divider(),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Historial de evaluaciones',
                        style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1E293B))),
                    TextButton(
                      onPressed: _cargarHistorial,
                      child: const Text('🔄 Actualizar'),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                if (_cargandoHistorial)
                  const Center(child: CircularProgressIndicator())
                else if (_historial.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: const Center(
                      child: Text('No hay evaluaciones aún.',
                          style: TextStyle(color: Colors.grey)),
                    ),
                  )
                else
                  ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _historial.length,
                    itemBuilder: (context, index) {
                      final eval   = _historial[index];
                      final status = eval['status'] ?? 'pending';
                      final fecha  = eval['created_at'] != null
                          ? eval['created_at']
                              .toString()
                              .substring(0, 16)
                              .replaceAll('T', ' ')
                          : 'Sin fecha';
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10)),
                        child: ListTile(
                          leading: Text(
                            status == 'completed'
                                ? '✅'
                                : status == 'error'
                                    ? '❌'
                                    : '⏳',
                            style: const TextStyle(fontSize: 24),
                          ),
                          title: Text(
                            eval['image_path'] ?? 'Imagen',
                            style: const TextStyle(
                                fontWeight: FontWeight.w500),
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(fecha,
                              style: const TextStyle(
                                  color: Colors.grey, fontSize: 12)),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color:
                                  _colorStatus(status).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              status,
                              style: TextStyle(
                                  color: _colorStatus(status),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}