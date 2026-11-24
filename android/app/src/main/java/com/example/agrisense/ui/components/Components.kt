package com.example.agrisense.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.theme.agri

@Composable
fun AppCard(modifier: Modifier = Modifier, onClick: (() -> Unit)? = null, color: Color? = null, border: Color? = null,
            content: @Composable ColumnScope.() -> Unit) {
    val a = agri
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(color ?: a.surface)
            .border(1.dp, border ?: a.line, RoundedCornerShape(18.dp))
            .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier)
            .padding(16.dp),
        content = content,
    )
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, icon: ImageVector? = null, loading: Boolean = false,
                  enabled: Boolean = true, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled && !loading, modifier = modifier.fillMaxWidth().heightIn(min = 52.dp),
        shape = RoundedCornerShape(14.dp)) {
        if (loading) CircularProgressIndicator(Modifier.size(20.dp), color = Color.White, strokeWidth = 2.dp)
        else if (icon != null) Icon(icon, null, Modifier.size(20.dp))
        Spacer(Modifier.width(8.dp))
        Text(tr(text), style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold))
    }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, icon: ImageVector? = null, loading: Boolean = false, onClick: () -> Unit) {
    val a = agri
    Button(onClick = onClick, enabled = !loading, modifier = modifier.heightIn(min = 52.dp), shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = a.mint, contentColor = a.primaryDark)) {
        if (loading) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
        else if (icon != null) Icon(icon, null, Modifier.size(20.dp))
        Spacer(Modifier.width(6.dp))
        Text(tr(text), style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
fun DangerButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val a = agri
    OutlinedButton(onClick = onClick, modifier = modifier.heightIn(min = 52.dp), shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, a.danger), colors = ButtonDefaults.outlinedButtonColors(contentColor = a.danger)) {
        Text(tr(text), style = MaterialTheme.typography.labelLarge)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppBar(title: String, onBack: (() -> Unit)? = null, actions: @Composable RowScope.() -> Unit = {}) {
    TopAppBar(
        title = { Text(tr(title), style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis) },
        navigationIcon = { if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, tr("Back")) } },
        actions = actions,
        colors = TopAppBarDefaults.topAppBarColors(containerColor = agri.background),
    )
}

@Composable
fun Field(label: String, value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier, hint: String? = null,
          error: String? = null, placeholder: String? = null, keyboard: KeyboardType = KeyboardType.Text,
          password: Boolean = false, singleLine: Boolean = true, minLines: Int = 1) {
    val a = agri
    Column(modifier) {
        Text(tr(label), style = MaterialTheme.typography.labelLarge, color = a.ink)
        Spacer(Modifier.height(4.dp))
        OutlinedTextField(
            value = value, onValueChange = onChange, modifier = Modifier.fillMaxWidth(), singleLine = singleLine, minLines = minLines,
            isError = error != null, shape = RoundedCornerShape(14.dp),
            placeholder = placeholder?.let { { Text(it, color = a.muted) } },
            keyboardOptions = KeyboardOptions(keyboardType = keyboard),
            visualTransformation = if (password) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
            colors = OutlinedTextFieldDefaults.colors(unfocusedContainerColor = a.surface, focusedContainerColor = a.surface,
                unfocusedBorderColor = a.line),
        )
        if (error != null) Text(tr(error), color = a.danger, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 2.dp))
        else if (hint != null) Text(tr(hint), color = a.muted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 2.dp))
    }
}

/** Dropdown whose options come from the API. [options] = value to label. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Select(label: String, value: String, options: List<Pair<String, String>>, onChange: (String) -> Unit,
           modifier: Modifier = Modifier, error: String? = null, translateLabels: Boolean = false) {
    var open by remember { mutableStateOf(false) }
    val a = agri
    val shown = options.firstOrNull { it.first == value }?.second ?: ""
    Column(modifier) {
        Text(tr(label), style = MaterialTheme.typography.labelLarge, color = a.ink)
        Spacer(Modifier.height(4.dp))
        ExposedDropdownMenuBox(expanded = open, onExpandedChange = { open = it }) {
            OutlinedTextField(
                value = if (translateLabels) tr(shown) else shown, onValueChange = {}, readOnly = true, singleLine = true,
                isError = error != null, shape = RoundedCornerShape(14.dp),
                placeholder = { Text(tr("Select…"), color = a.muted) },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(open) },
                modifier = Modifier.fillMaxWidth().menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable),
                colors = OutlinedTextFieldDefaults.colors(unfocusedContainerColor = a.surface, focusedContainerColor = a.surface, unfocusedBorderColor = a.line),
            )
            ExposedDropdownMenu(expanded = open, onDismissRequest = { open = false }, containerColor = agri.surface) {
                options.forEach { (v, l) ->
                    DropdownMenuItem(text = { Text(if (translateLabels) tr(l) else l) }, onClick = { onChange(v); open = false })
                }
            }
        }
        if (error != null) Text(tr(error), color = a.danger, style = MaterialTheme.typography.bodySmall)
    }
}

/** Custom input vs. random real sample from the dataset (same switch as the dashboard). */
@Composable
fun ModeSwitch(auto: Boolean, onChange: (Boolean) -> Unit) {
    val a = agri
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(a.mint).border(1.dp, a.line, RoundedCornerShape(14.dp)).padding(4.dp)) {
        listOf(false to ("My values" to Icons.Filled.Edit), true to ("Sample from dataset" to Icons.Filled.Shuffle)).forEach { (isAuto, p) ->
            val sel = auto == isAuto
            Row(
                Modifier.weight(1f).heightIn(min = 44.dp).clip(RoundedCornerShape(10.dp))
                    .background(if (sel) a.surface else Color.Transparent).clickable { onChange(isAuto) }.padding(horizontal = 8.dp),
                horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(p.second, null, Modifier.size(18.dp), tint = if (sel) a.primaryDark else a.muted)
                Spacer(Modifier.width(6.dp))
                Text(tr(p.first), style = MaterialTheme.typography.labelLarge, color = if (sel) a.primaryDark else a.muted, maxLines = 2)
            }
        }
    }
}

@Composable
fun Chip(text: String, fg: Color, bg: Color, icon: ImageVector? = null, translate: Boolean = true) {
    Row(Modifier.clip(CircleShape).background(bg).padding(horizontal = 10.dp, vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
        if (icon != null) { Icon(icon, null, Modifier.size(15.dp), tint = fg); Spacer(Modifier.width(4.dp)) }
        Text(if (translate) tr(text) else text, color = fg, style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
fun Note(text: String, warn: Boolean = false, translate: Boolean = true) {
    val a = agri
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(if (warn) a.warnBg else a.mint).padding(12.dp)) {
        Icon(if (warn) Icons.Filled.Warning else Icons.Filled.Info, null, Modifier.size(18.dp), tint = if (warn) a.warn else a.primaryDark)
        Spacer(Modifier.width(8.dp))
        Text(if (translate) tr(text) else text, style = MaterialTheme.typography.bodySmall, color = if (warn) a.warn else a.ink)
    }
}

@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) =
    Text(tr(text).uppercase(), modifier = modifier.padding(top = 6.dp, bottom = 2.dp), style = MaterialTheme.typography.labelMedium, color = agri.muted)

@Composable
fun Loading(modifier: Modifier = Modifier) =
    Box(modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() }

@Composable
fun ErrorState(message: String, onRetry: (() -> Unit)? = null) {
    val a = agri
    Column(Modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(Icons.Filled.ErrorOutline, null, Modifier.size(40.dp), tint = a.muted)
        Spacer(Modifier.height(8.dp))
        Text(tr(message), color = a.muted, style = MaterialTheme.typography.bodyMedium)
        if (onRetry != null) { Spacer(Modifier.height(12.dp)); SecondaryButton("Retry", onClick = onRetry) }
    }
}

@Composable
fun EmptyState(icon: ImageVector, text: String, action: (@Composable () -> Unit)? = null) {
    val a = agri
    Column(Modifier.fillMaxWidth().padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.size(56.dp).clip(RoundedCornerShape(16.dp)).background(a.mint2), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = a.primary)
        }
        Spacer(Modifier.height(10.dp))
        Text(tr(text), color = a.muted, style = MaterialTheme.typography.bodyMedium)
        if (action != null) { Spacer(Modifier.height(12.dp)); action() }
    }
}

/** Horizontal bar used for probabilities, contributions and nutrient levels. */
@Composable
fun BarRow(label: String, value: Double, max: Double, valueText: String, color: Color, translate: Boolean = false) {
    val a = agri
    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(Modifier.fillMaxWidth()) {
            Text(if (translate) tr(label) else label, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(valueText, style = MaterialTheme.typography.labelMedium, color = a.muted)
        }
        Box(Modifier.fillMaxWidth().height(8.dp).clip(CircleShape).background(a.line)) {
            Box(Modifier.fillMaxWidth(((value / max).coerceIn(0.0, 1.0)).toFloat()).height(8.dp).clip(CircleShape).background(color))
        }
    }
}

@Composable
fun IconTile(icon: ImageVector, tint: Color, bg: Color, size: Dp = 40.dp) =
    Box(Modifier.size(size).clip(RoundedCornerShape(12.dp)).background(bg), contentAlignment = Alignment.Center) {
        Icon(icon, null, tint = tint, modifier = Modifier.size(size * 0.55f))
    }

@Composable
fun Screen(content: @Composable ColumnScope.() -> Unit) =
    Column(Modifier.fillMaxSize().background(agri.background).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
