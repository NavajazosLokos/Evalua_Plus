import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _mostrarRegistro = false;
  final _nameController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    Map<String, dynamic> resultado;

    if (_mostrarRegistro) {
      resultado = await AuthService.registro(
        _nameController.text.trim(),
        _emailController.text.trim(),
        _passwordController.text,
      );
    } else {
      resultado = await AuthService.login(
        _emailController.text.trim(),
        _passwordController.text,
      );
    }

    setState(() => _isLoading = false);

    if (!mounted) return;

    if (resultado['success']) {
      if (_mostrarRegistro) {
        // Después de registrarse, ir al login
        setState(() => _mostrarRegistro = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cuenta creada. Inicia sesión.')),
        );
      } else {
        // Ir a la pantalla principal
        Navigator.pushReplacementNamed(context, '/home');
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(resultado['message'] ?? 'Ocurrió un error'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Logo / Título
                      const Icon(Icons.analytics_outlined, size: 56, color: Color(0xFF2563EB)),
                      const SizedBox(height: 12),
                      Text(
                        'EvaluaPlus',
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: const Color(0xFF1E293B),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _mostrarRegistro ? 'Crea tu cuenta' : 'Inicia sesión para continuar',
                        style: const TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 28),

                      // Campo nombre (solo en registro)
                      if (_mostrarRegistro) ...[
                        TextFormField(
                          controller: _nameController,
                          decoration: _inputDecoration('Nombre completo', Icons.person_outline),
                          validator: (v) => v == null || v.isEmpty ? 'Ingresa tu nombre' : null,
                        ),
                        const SizedBox(height: 16),
                      ],

                      // Campo email
                      TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        decoration: _inputDecoration('Correo electrónico', Icons.email_outlined),
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'Ingresa tu correo';
                          if (!v.contains('@')) return 'Correo inválido';
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Campo contraseña
                      TextFormField(
                        controller: _passwordController,
                        obscureText: _obscurePassword,
                        decoration: _inputDecoration(
                          'Contraseña',
                          Icons.lock_outline,
                          suffix: IconButton(
                            icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility),
                            onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                          ),
                        ),
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'Ingresa tu contraseña';
                          if (_mostrarRegistro && v.length < 6) return 'Mínimo 6 caracteres';
                          return null;
                        },
                      ),
                      const SizedBox(height: 28),

                      // Botón principal
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _submit,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF2563EB),
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          child: _isLoading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                                )
                              : Text(
                                  _mostrarRegistro ? 'Crear cuenta' : 'Iniciar sesión',
                                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                                ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Cambiar entre login y registro
                      TextButton(
                        onPressed: () => setState(() => _mostrarRegistro = !_mostrarRegistro),
                        child: Text(
                          _mostrarRegistro
                              ? '¿Ya tienes cuenta? Inicia sesión'
                              : '¿No tienes cuenta? Regístrate',
                          style: const TextStyle(color: Color(0xFF2563EB)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String label, IconData icon, {Widget? suffix}) {
    return InputDecoration(
      labelText: label,
      prefixIcon: Icon(icon, color: Colors.grey),
      suffixIcon: suffix,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Color(0xFF2563EB)),
      ),
      filled: true,
      fillColor: Colors.white,
    );
  }
}