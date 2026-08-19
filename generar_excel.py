import pandas as pd

# 1. Creamos los datos de los Clientes
df_clientes = pd.DataFrame({
    'ID_Cliente': ['CLI-001', 'CLI-002'],
    'Nombre_Completo': ['Juan Pérez', 'María López'],
    'Telefono': ['0414-1234567', '0424-7654321'],
    'Direccion': ['Calle 4, Local 12', 'Av. Principal, Kiosco'],
    'Zona_Ruta': ['Centro', 'Norte']
})

# 2. Creamos los datos de los Préstamos
df_prestamos = pd.DataFrame({
    'ID_Prestamo': ['PRE-101', 'PRE-102'],
    'ID_Cliente': ['CLI-001', 'CLI-002'],
    'Fecha_Inicio': ['18/08/2026', '15/08/2026'],
    'Capital': [100.0, 200.0],
    'Interes_%': [0.20, 0.15],
    'Total_Deuda': [120.0, 230.0],
    'Modalidad': ['Diario', 'Semanal'],
    'Valor_Cuota': [4.0, 23.0],
    'Saldo_Pendiente': [120.0, 184.0],
    'Estado': ['Activo', 'Activo']
})

# 3. Creamos los datos de los Recaudos
df_recaudos = pd.DataFrame({
    'ID_Pago': ['PAG-001', 'PAG-002'],
    'Fecha_Pago': ['18/08/2026', '18/08/2026'],
    'ID_Prestamo': ['PRE-101', 'PRE-102'],
    'Cobrador': ['Carlos', 'Miguel'],
    'Monto_Recibido': [4.0, 46.0],
    'Tipo_Caja': ['Divisas', 'Efectivo Local'],
    'Notas': ['Pago completo', 'Adelantó 2 cuotas']
})

# 4. Guardamos todo en un solo archivo Excel con sus 3 pestañas
nombre_archivo = 'cartera_prestamos.xlsx'

with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
    df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
    df_prestamos.to_excel(writer, sheet_name='Prestamos', index=False)
    df_recaudos.to_excel(writer, sheet_name='Recaudos', index=False)

print(f"¡Listo! El archivo '{nombre_archivo}' ha sido creado en esta carpeta.")
