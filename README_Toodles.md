# 🧠 ToodlesBot v6 — Documentación General Extendida

ToodlesBot es un bot musical para Discord con un enfoque modular, eficiente, extensible y altamente personalizado. La versión v6 representa una reescritura completa respecto a la v5, no solo replicando sus funcionalidades sino también integrando una arquitectura desacoplada, mecanismos de seguridad más avanzados, mejoras en la experiencia de usuario y una interfaz gráfica significativamente más rica. Esta nueva versión ha sido construida con miras a escalabilidad futura, facilidad de mantenimiento y una base sólida para nuevas integraciones como análisis de datos, comandos slash y extensiones de comunidad.

---

## 📁 Estructura de Archivos y Módulos

| Archivo       | Propósito principal                                                                 |
| ------------- | ----------------------------------------------------------------------------------- |
| `main.py`     | Punto de entrada del bot. Carga y orquesta los cogs en el orden seguro y correcto.  |
| `sznMusic.py` | Módulo central de reproducción: comandos musicales, integración con Spotify, radio. |
| `sznQueue.py` | Gestión completa de la cola: agregar, mover, eliminar, precargar en background.     |
| `sznUI.py`    | Embeds, botones interactivos, vistas personalizadas como `SearchResultsView`.       |
| `sznUtils.py` | Funciones utilitarias: manejo de cookies, encriptación, validaciones y más.         |
| `sznDB.py`    | Base de datos y ORM: favoritos, historial, top de canciones (SQLite).               |

---

## 🎛️ Funciones Clave del Bot

### 🎵 Reproducción Multimedia

- `td?p [búsqueda|URL]` — Reproduce canciones desde YouTube o enlaces de Spotify (track/playlist).
- `td?pause`, `td?resume`, `td?skip`, `td?stop`, `td?np` — Controles básicos de reproducción.
- `td?queue` — Muestra la cola actual con formato embellecido.
- `td?queueui` — Abre una vista interactiva con controles y acciones rápidas.

### 🔁 Modo Radio Emocional

- `td?radio [temperatura|off]` — Activa un modo de radio dinámica basado en recomendaciones de Spotify. Incluye control de "temperatura" emocional (valence/energy).
- `td?favradio` — Crea una estación basada en los favoritos de los usuarios activos en voz.

### 🔍 Búsqueda Interactiva y Precisa

- `td?search <búsqueda>` — Devuelve resultados de YouTube y permite elegir entre ellos con botones interactivos.
- Resultados se cargan con metadatos y pueden ser añadidos a la cola con un clic.

### 🎧 Sistema de Favoritos y Estadísticas

- `td?like`, `td?unlike`, `td?liked` — Marca canciones como favoritas y consúltalas por usuario.
- `td?top`, `td?historial` — Consulta el top global de reproducciones y tu historial personal.

---

## 🔐 Manejo Jerárquico de Cookies

ToodlesBot v6 requiere autenticación con cookies para acceder a contenido en YouTube que no está disponible públicamente:

- **Admins** pueden subir cookies persistentes, que quedan cifradas y almacenadas en la base de datos.
- **Usuarios sin permisos** pueden subir cookies temporales, que expiran automáticamente a las 6 horas.
- El bot gestiona automáticamente qué cookie está activa, priorizando la temporal si aún no ha caducado, y haciendo fallback a la última persistente.
- Todas las cookies pueden enviarse por archivo o pegadas directamente como texto.

Este diseño protege la privacidad, mantiene funcionalidad y reduce riesgos de sobreescritura no deseada.

---

## ⚙️ Arquitectura Modular y Control de Dependencias

- Todos los módulos son **cogs desacoplados** que comunican entre sí a través de `bot.get_cog(...)`.
- No existen `import` cruzados entre cogs. Esto previene errores de carga circular y mantiene un diseño limpio.
- `main.py` se encarga de cargar los cogs en el orden correcto: primero base de datos, luego gestor de cola, interfaz y finalmente el módulo de música.
- Se usan locks internos (`threading.Lock`) para manejar la cola de reproducción de forma segura.
- Precarga automática de canciones próximas para evitar latencias perceptibles.

---

## 🧾 Comparación entre v5 y v6 (Migración y Mejoras)

| Característica          | v5                            | ✅ v6 (actual)                                                        |
| ----------------------- | ----------------------------- | -------------------------------------------------------------------- |
| Estructura              | Monolítica                    | Modular, cogs desacoplados                                           |
| Cola                    | Lista manual                  | `QueueManager` + precarga anticipada + thread-safe                   |
| Cookies                 | Solo por entorno `.env`       | Jerárquico: temporal vs persistente, cifrado con Fernet              |
| Modo radio              | Básico                        | Spotify integrado, con control de temperatura y fallback inteligente |
| Favoritos               | No existía                    | ORM en SQLite + comandos dedicados                                   |
| Interfaz (UI)           | `ctx.send(...)` plano         | `sznUI`: embeds, botones, vistas personalizadas                      |
| Búsqueda                | Manual (reproduce lo primero) | Interactiva, paginada, con selección visual                          |
| Seguridad entre módulos | Frágil                        | Alta: acceso solo por `get_cog`, sin imports directos                |
| Precarga de canciones   | ❌                             | ✅ Precarga en background antes de sonar                              |

---

## 🧠 Conclusión Técnica y Proyección

ToodlesBot v6 no es sólo una mejora evolutiva sobre la versión anterior, sino un rediseño integral con visión de largo plazo. Su estructura modular, su integración con Spotify, la interfaz reactiva y el manejo seguro de datos lo convierten en un bot musical de calidad profesional, listo para integrarse en comunidades exigentes, ambientes educativos o incluso sistemas con requisitos avanzados de automatización.

La próxima versión, **v6.1**, buscará consolidar estas bases con mejoras en UX, más controles visuales y herramientas de descubrimiento musical para todos los miembros del servidor.

---

¡Gracias por usar ToodlesBot! 🎶
